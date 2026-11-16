import json
from datetime import UTC
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select

from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.audit.service import record
from app.modules.borrowing.models import Loan, LoanItem
from app.modules.inventory import service as inventory
from app.modules.inventory.models import Equipment


def scoped(user):
    query = select(Loan)
    return query.where(Loan.student_id == user.id) if user.role == "student" else query


def get_loan(db, loan_id, user, lock=False):
    query = scoped(user).where(Loan.id == loan_id)
    loan = db.scalar(query.with_for_update() if lock else query)
    if not loan:
        raise AppError(404, "NOT_FOUND", "Không tìm thấy phiếu mượn")
    return loan


def create(db, body, actor, request_key=None):
    if body.due_at <= utcnow():
        raise AppError(422, "INVALID_DUE_DATE", "Hạn trả phải sau thời điểm gửi yêu cầu")
    normalized = body.model_dump(mode="json")
    normalized["items"] = sorted(normalized["items"], key=lambda x: x["equipment_id"])
    normalized["due_at"] = body.due_at.astimezone(UTC).isoformat()
    fingerprint = sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    if request_key:
        # Serialize same-user creation to avoid duplicate concurrent idempotency keys.
        from app.modules.identity.models import User

        db.scalar(select(User).where(User.id == actor.id).with_for_update())
        existing = db.scalar(
            select(Loan).where(Loan.student_id == actor.id, Loan.request_key == request_key)
        )
        if existing:
            if existing.request_hash != fingerprint:
                raise AppError(
                    409, "IDEMPOTENCY_CONFLICT", "Khóa idempotency đã dùng cho nội dung khác"
                )
            return existing
    for line in body.items:
        inventory.get_equipment(db, line.equipment_id)
    loan = Loan(
        code=f"LOAN-{uuid4().hex[:12].upper()}",
        student_id=actor.id,
        due_at=body.due_at,
        request_key=request_key,
        request_hash=fingerprint,
    )
    loan.items = [LoanItem(equipment_id=x.equipment_id, quantity=x.quantity) for x in body.items]
    db.add(loan)
    db.flush()
    record(
        db,
        actor,
        "loan",
        loan.id,
        "LoanRequested",
        after={"status": "PENDING", "due_at": loan.due_at.isoformat()},
    )
    return loan


def transition(db, loan_id, action, actor, body=None):
    loan = get_loan(db, loan_id, actor, lock=True)
    before = {"status": loan.status, "due_at": loan.due_at.isoformat()}
    if action != "cancel" and actor.role not in ("staff", "admin"):
        raise AppError(403, "FORBIDDEN", "Chỉ cán bộ được thực hiện thao tác này")
    transitions = {
        "approve": ("PENDING", "APPROVED"),
        "reject": ("PENDING", "REJECTED"),
        "handover": ("APPROVED", "BORROWED"),
        "return": ("BORROWED", "RETURNED"),
    }
    if action == "cancel":
        if loan.status not in ("PENDING", "APPROVED"):
            raise AppError(409, "INVALID_TRANSITION", "Chỉ hủy được phiếu trước khi bàn giao")
        if actor.role == "student" and loan.status != "PENDING":
            raise AppError(403, "FORBIDDEN", "Phiếu đã duyệt chỉ có cán bộ được hủy")
        target = "CANCELLED"
    else:
        origin, target = transitions[action]
        if loan.status != origin:
            raise AppError(
                409,
                "INVALID_TRANSITION",
                f"Không thể thực hiện {action} từ trạng thái {loan.status}",
            )
    if body and body.due_at:
        if action != "approve" or body.due_at <= utcnow():
            raise AppError(422, "INVALID_DUE_DATE", "Chỉ chỉnh hạn trả hợp lệ khi duyệt phiếu")
        loan.due_at = body.due_at
    quantities = {line.equipment_id: line.quantity for line in loan.items}
    now = utcnow()
    if action == "approve":
        if loan.due_at <= now:
            raise AppError(409, "DUE_DATE_PASSED", "Hạn trả đã qua; hãy điều chỉnh trước khi duyệt")
        inventory.reserve(db, quantities)
        loan.approved_at, loan.approved_by = now, actor.id
    elif action == "reject":
        if not body or not body.reason:
            raise AppError(422, "REASON_REQUIRED", "Phải nhập lý do từ chối")
        loan.rejection_reason = body.reason
    elif action == "handover":
        loan.handed_over_at = now
    elif action == "return":
        inventory.release(db, quantities)
        loan.returned_at = now
    elif action == "cancel" and loan.status == "APPROVED":
        inventory.release(db, quantities)
    loan.status = target
    db.flush()
    record(
        db,
        actor,
        "loan",
        loan.id,
        f"Loan{target.title()}",
        before,
        {"status": target, "due_at": loan.due_at.isoformat(), "reason": loan.rejection_reason},
    )
    if action in ("approve", "return"):
        from app.infrastructure.blockchain.service import enqueue

        enqueue(db, loan, "BorrowApproved" if action == "approve" else "EquipmentReturned", now)
    return loan


def present(db, loan, full=False):
    result = {
        key: getattr(loan, key)
        for key in [
            "id",
            "code",
            "student_id",
            "status",
            "requested_at",
            "due_at",
            "approved_at",
            "handed_over_at",
            "returned_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
    }
    result["items"] = []
    for line in loan.items:
        item = db.get(Equipment, line.equipment_id)
        result["items"].append(
            {
                "equipment_id": line.equipment_id,
                "code": item.code,
                "name": item.name,
                "quantity": line.quantity,
                "unit": item.unit,
            }
        )
    from app.infrastructure.blockchain.models import BlockchainTransaction

    transactions = list(
        db.scalars(
            select(BlockchainTransaction)
            .where(BlockchainTransaction.loan_id == loan.id)
            .order_by(BlockchainTransaction.created_at)
        )
    )
    result["transactions"] = [
        {
            key: getattr(tx, key)
            for key in [
                "id",
                "event_type",
                "operation_id",
                "data_hash",
                "tx_hash",
                "block_number",
                "status",
                "error_message",
            ]
        }
        for tx in transactions
    ]
    if full:
        result["timeline"] = [
            {"action": event.action, "created_at": event.created_at, "details": event.after_json}
            for event in db.scalars(
                select(AuditLog)
                .where(AuditLog.entity_type == "loan", AuditLog.entity_id == loan.id)
                .order_by(AuditLog.created_at, AuditLog.id)
            )
        ]
    return result
