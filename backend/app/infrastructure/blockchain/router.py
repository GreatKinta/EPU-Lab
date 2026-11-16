from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import CurrentUser, Db, Staff
from app.infrastructure.blockchain.adapter import ChainAdapter
from app.infrastructure.blockchain.hashing import loan_ref, operation_id, snapshot_hash
from app.infrastructure.blockchain.models import BlockchainTransaction, OutboxEvent
from app.modules.audit.service import record
from app.modules.borrowing.service import get_loan

router = APIRouter(tags=["blockchain"])


@router.get("/loans/{loan_id}/verify")
def verify(loan_id: UUID, db: Db, user: CurrentUser):
    get_loan(db, loan_id, user)
    transactions = list(
        db.scalars(
            select(BlockchainTransaction)
            .where(BlockchainTransaction.loan_id == loan_id)
            .order_by(BlockchainTransaction.created_at)
        )
    )
    if not transactions:
        return {"status": "NOT_RECORDED", "network": "Hardhat Local · 31337", "records": []}
    records = []
    try:
        adapter = ChainAdapter()
    except Exception:
        adapter = None
    for tx in transactions:
        event = db.get(OutboxEvent, tx.outbox_event_id)
        expected = None
        try:
            expected = snapshot_hash(event.payload)
        except (ValueError, TypeError):
            pass
        result = {
            "event_id": str(event.id),
            "event_type": tx.event_type,
            "operation_id": tx.operation_id,
            "tx_hash": tx.tx_hash,
            "block_number": tx.block_number,
            "stored_hash": tx.data_hash,
            "computed_hash": expected,
            "chain_hash": None,
            "snapshot": event.payload,
            "error": tx.error_message,
        }
        if (
            expected != tx.data_hash
            or tx.operation_id != operation_id(event.id)
            or event.payload.get("loan_ref") != loan_ref(loan_id)
        ):
            result.update(status="MISMATCH", reason="Snapshot hoặc định danh đã thay đổi")
        elif adapter is None:
            result.update(
                status="CHAIN_UNAVAILABLE",
                reason="Không kết nối được mạng hoặc chưa triển khai contract",
            )
        else:
            try:
                actual = adapter.read(operation_id(event.id))
                result["chain_hash"] = actual["data_hash"] if actual["kind"] else None
                if not actual["kind"]:
                    result.update(
                        status="PENDING"
                        if tx.status in ("PENDING", "SUBMITTED")
                        else "NOT_RECORDED",
                        reason="Chưa có bằng chứng trên contract",
                    )
                elif (
                    actual["data_hash"] == expected
                    and actual["loan_ref"] == loan_ref(loan_id)
                    and actual["kind"] == (1 if tx.event_type == "BorrowApproved" else 2)
                ):
                    result.update(
                        status="VERIFIED",
                        reason="Hash snapshot khớp dữ liệu đọc trực tiếp từ contract",
                    )
                else:
                    result.update(
                        status="MISMATCH", reason="Bằng chứng trên contract không khớp snapshot"
                    )
            except Exception:
                result.update(status="CHAIN_UNAVAILABLE", reason="Lỗi đọc mạng Blockchain")
        records.append(result)
    statuses = {x["status"] for x in records}
    status = next(
        (s for s in ["MISMATCH", "CHAIN_UNAVAILABLE", "PENDING", "NOT_RECORDED"] if s in statuses),
        "VERIFIED",
    )
    return {"status": status, "network": "Hardhat Local · 31337", "records": records}


@router.post("/blockchain/events/{event_id}/retry")
def retry(event_id: UUID, db: Db, actor: Staff):
    event = db.get(OutboxEvent, event_id, with_for_update=True)
    if not event:
        raise AppError(404, "NOT_FOUND", "Không tìm thấy sự kiện")
    if event.status != "FAILED":
        raise AppError(409, "INVALID_RETRY", "Chỉ thử lại sự kiện đã thất bại")
    tx = db.scalar(
        select(BlockchainTransaction).where(BlockchainTransaction.outbox_event_id == event.id)
    )
    if tx.raw_transaction:
        try:
            receipt = ChainAdapter().receipt(tx.tx_hash)
            if receipt and receipt["status"] == 0:
                tx.raw_transaction = None
                tx.tx_hash = None
                tx.nonce = None
        except Exception:
            pass  # Keep exact signed bytes if submission is uncertain.
    event.status = "PENDING"
    event.attempt_count = 0
    event.next_retry_at = utcnow()
    event.last_error = None
    tx.status = "SUBMITTED" if tx.raw_transaction else "PENDING"
    tx.error_message = None
    record(
        db,
        actor,
        "loan",
        event.aggregate_id,
        "BlockchainRetryRequested",
        after={"event_id": str(event.id)},
    )
    return {"status": "PENDING"}
