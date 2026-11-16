from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query
from sqlalchemy import func, select

from app.core.security import CurrentUser, Db
from app.modules.borrowing import service
from app.modules.borrowing.models import Loan
from app.modules.borrowing.schemas import LoanCreate, TransitionInput

router = APIRouter(prefix="/loans", tags=["borrowing"])


@router.get("")
def list_loans(
    db: Db,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Literal["PENDING", "APPROVED", "REJECTED", "BORROWED", "RETURNED", "CANCELLED"]
    | None = None,
):
    query = service.scoped(user)
    if status:
        query = query.where(Loan.status == status)
    return {
        "items": [
            service.present(db, x)
            for x in db.scalars(
                query.order_by(Loan.created_at.desc(), Loan.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201)
def create_loan(
    body: LoanCreate,
    db: Db,
    user: CurrentUser,
    idempotency_key: Annotated[str | None, Header(max_length=100)] = None,
):
    return service.present(db, service.create(db, body, user, idempotency_key), full=True)


@router.get("/{loan_id}")
def detail(loan_id: UUID, db: Db, user: CurrentUser):
    return service.present(db, service.get_loan(db, loan_id, user), full=True)


@router.post("/{loan_id}/{action}")
def action(
    loan_id: UUID,
    action: Literal["approve", "reject", "handover", "return", "cancel"],
    db: Db,
    user: CurrentUser,
    body: TransitionInput | None = None,
):
    return service.present(db, service.transition(db, loan_id, action, user, body), full=True)
