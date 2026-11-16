from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.db import utcnow
from app.core.security import CurrentUser, Db
from app.infrastructure.blockchain.models import BlockchainTransaction
from app.modules.audit.models import AuditLog
from app.modules.borrowing.models import Loan, LoanItem
from app.modules.borrowing.service import scoped
from app.modules.inventory.models import Equipment

router = APIRouter(tags=["reporting"])


@router.get("/dashboard/summary")
def summary(db: Db, user: CurrentUser):
    query = scoped(user)

    def count(states, overdue=False):
        q = query.where(Loan.status.in_(states))
        if overdue:
            q = q.where(Loan.due_at < utcnow())
        return db.scalar(select(func.count()).select_from(q.subquery()))

    popular = (
        select(Equipment.name, func.sum(LoanItem.quantity).label("quantity"))
        .join(LoanItem, LoanItem.equipment_id == Equipment.id)
        .join(Loan, Loan.id == LoanItem.loan_id)
        .where(Loan.status.in_(["APPROVED", "BORROWED", "RETURNED"]))
    )
    tx = (
        select(func.count())
        .select_from(BlockchainTransaction)
        .join(Loan)
        .where(BlockchainTransaction.status == "CONFIRMED")
    )
    if user.role == "student":
        popular = popular.where(Loan.student_id == user.id)
        tx = tx.where(Loan.student_id == user.id)
    rows = db.execute(
        popular.group_by(Equipment.id, Equipment.name)
        .order_by(func.sum(LoanItem.quantity).desc(), Equipment.name)
        .limit(5)
    ).all()
    return {
        "equipment_count": db.scalar(
            select(func.count()).select_from(Equipment).where(Equipment.deleted_at.is_(None))
        ),
        "available_units": db.scalar(
            select(
                func.coalesce(func.sum(Equipment.quantity_total - Equipment.quantity_reserved), 0)
            ).where(Equipment.deleted_at.is_(None))
        ),
        "active_loans": count(["APPROVED", "BORROWED"]),
        "pending_loans": count(["PENDING"]),
        "overdue_loans": count(["BORROWED"], True),
        "confirmed_transactions": db.scalar(tx),
        "recent_loans": [
            {"id": x.id, "code": x.code, "status": x.status, "due_at": x.due_at}
            for x in db.scalars(query.order_by(Loan.created_at.desc()).limit(5))
        ],
        "popular_equipment": [{"name": row.name, "quantity": row.quantity} for row in rows],
    }


@router.get("/audit/events")
def audit(
    db: Db, user: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100)
):
    query = select(AuditLog)
    if user.role == "student":
        query = query.where(AuditLog.actor_user_id == user.id)
    return {
        "items": [
            {
                "id": x.id,
                "entity_type": x.entity_type,
                "entity_id": x.entity_id,
                "action": x.action,
                "created_at": x.created_at,
                "before": x.before_json,
                "after": x.after_json,
            }
            for x in db.scalars(
                query.order_by(AuditLog.created_at.desc(), AuditLog.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "page": page,
        "page_size": page_size,
    }
