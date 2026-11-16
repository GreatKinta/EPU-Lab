from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Entity, utcnow


class OutboxEvent(Entity, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("aggregate_id", "event_type"),
        Index("ix_outbox_poll", "status", "next_retry_at", "created_at"),
    )
    aggregate_type: Mapped[str] = mapped_column(String(40), default="loan")
    aggregate_id: Mapped[UUID] = mapped_column(ForeignKey("loans.id"))
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockchainTransaction(Entity, Base):
    __tablename__ = "blockchain_transactions"
    outbox_event_id: Mapped[UUID] = mapped_column(ForeignKey("outbox_events.id"), unique=True)
    loan_id: Mapped[UUID] = mapped_column(ForeignKey("loans.id"))
    operation_id: Mapped[str] = mapped_column(String(66), unique=True)
    event_type: Mapped[str] = mapped_column(String(40))
    data_hash: Mapped[str] = mapped_column(String(66))
    tx_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    raw_transaction: Mapped[str | None] = mapped_column(Text)
    nonce: Mapped[int | None]
    block_number: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text)
