from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from refund_pilot.db.base import Base

if TYPE_CHECKING:
    from refund_pilot.db.models.conversation import Conversation
    from refund_pilot.db.models.order import Order


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    tier: Mapped[str] = mapped_column(
        Enum("standard", "premium", "vip", name="customer_tier"), nullable=False, default="standard"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list[Order]] = relationship("Order", back_populates="customer", lazy="selectin")
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="customer", lazy="selectin"
    )
