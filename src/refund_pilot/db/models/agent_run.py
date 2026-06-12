from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from refund_pilot.db.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True
    )
    input_message: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(
        Enum("approved", "denied", "escalated", "fallback", "restate", name="agent_decision"),
        nullable=False,
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    policy_clauses_cited: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    trace_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    model_used: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    langsmith_run_id: Mapped[str | None] = mapped_column(String(255))
    injection_detected: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
