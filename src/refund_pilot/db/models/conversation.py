from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from refund_pilot.db.base import Base

if TYPE_CHECKING:
    from refund_pilot.db.models.chat_message import ChatMessage
    from refund_pilot.db.models.customer import Customer


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("open", "closed", name="conversation_status"), nullable=False, default="open"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[Customer] = relationship("Customer", back_populates="conversations")
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        order_by="ChatMessage.created_at",
        lazy="selectin",
    )
