import sqlalchemy as sa
from uuid import UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.payment_status_enums import PaymentStatusEnum
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .order import Order

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        sa.UniqueConstraint("order_id", name="uq_payments_order_id"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    provider: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    provider_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[PaymentStatusEnum] = mapped_column(sa.Enum(PaymentStatusEnum, name="payment_status_enum", create_type=False), server_default=sa.text("'pending'::payment_status_enum"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    currency: Mapped[CurrencyEnum] = mapped_column(sa.Enum(CurrencyEnum, name="currency_enum", create_type=False), server_default=sa.text("'USD'::currency_enum"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payment", lazy="joined")