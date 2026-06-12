from __future__ import annotations

from typing import Any, TypedDict

from refund_pilot.agent.tools import PolicyVerdict
from refund_pilot.db.models import Customer, Order
from refund_pilot.schemas.agent import AgentDecision, TraceStep


class AgentState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes."""

    # Required inputs
    conversation_id: str
    customer_id: str
    order_id: str
    current_message: str
    request_id: str
    task_id: str

    # Populated by nodes
    conversation_history: list[dict[str, Any]]
    customer: Customer | None
    policy_verdict: PolicyVerdict | None
    decision: AgentDecision | None
    injection_detected: bool

    # Internal node-to-node data (prefixed _)
    _order: Order | None
    _recent_refunds: int
    _escalation_reason: str
    _agent_start_ms: float
    _token_counts: dict[str, int]
    _run_id: str
    _model_used: str
    _trace_validate: TraceStep
    _trace_query_db: TraceStep
    _trace_policy: TraceStep
    _trace_escalate: TraceStep
    _trace_generate: TraceStep
