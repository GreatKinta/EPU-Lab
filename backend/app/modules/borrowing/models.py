from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Entity, utcnow


class Loan(Entity, Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','BORROWED','RETURNED','CANCELLED')",
            name="status",
        ),
        CheckConstraint("due_at > requested_at", name="due_after_request"),
        UniqueConstraint("student_id", "request_key"),
        Index("ix_loans_student_created", "student_id", "created_at"),
        Index("ix_loans_status_due", "status", "due_at"),
    )
    code: Mapped[str] = mapped_column(String(40), unique=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handed_over_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    request_key: Mapped[str | None] = mapped_column(String(100))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    items: Mapped[list["LoanItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class LoanItem(Entity, Base):
    __tablename__ = "loan_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        UniqueConstraint("loan_id", "equipment_id"),
    )
    loan_id: Mapped[UUID] = mapped_column(ForeignKey("loans.id"))
    equipment_id: Mapped[UUID] = mapped_column(ForeignKey("equipment.id"))
    quantity: Mapped[int]
