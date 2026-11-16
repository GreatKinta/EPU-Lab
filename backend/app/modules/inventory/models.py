from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Entity


class Equipment(Entity, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint("quantity_total >= 0", name="total_nonnegative"),
        CheckConstraint(
            "quantity_reserved >= 0 AND quantity_reserved <= quantity_total",
            name="reservation_valid",
        ),
        CheckConstraint("price >= 0", name="price_nonnegative"),
    )
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    image_path: Mapped[str | None] = mapped_column(String(200))
    product_type: Mapped[str] = mapped_column(String(100), index=True)
    quantity_total: Mapped[int] = mapped_column(default=0)
    quantity_reserved: Mapped[int] = mapped_column(default=0)
    unit: Mapped[str] = mapped_column(String(30))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    @property
    def quantity_available(self):
        return self.quantity_total - self.quantity_reserved
