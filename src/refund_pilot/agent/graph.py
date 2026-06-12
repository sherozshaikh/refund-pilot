"""LangGraph StateGraph — wires nodes together, routing on policy verdict."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.agent.nodes import (
    node_check_refund_eligibility,
    node_escalate_to_human,
    node_generate_response,
    node_log_run,
    node_query_customer_db,
    node_validate_request,
)
from refund_pilot.agent.state import AgentState
from refund_pilot.core.config import PipelineConfig

NodeFn = Callable[[AgentState, AsyncSession, PipelineConfig], Awaitable[dict[str, Any]]]


def _route_after_policy(state: AgentState) -> str:
    """Route to escalate_to_human if verdict is escalated, else generate_response."""
    verdict = state.get("policy_verdict")
    if verdict and verdict.decision == "escalated":
        return "escalate_to_human"
    return "generate_response"


def build_graph(db: AsyncSession, config: PipelineConfig) -> Any:
    """Build and compile the refund agent StateGraph."""

    def _bind(fn: NodeFn) -> Callable[[AgentState], Awaitable[dict[str, Any]]]:
        async def _wrapped(state: AgentState) -> dict[str, Any]:
            return await fn(state, db, config)

        _wrapped.__name__ = fn.__name__
        return _wrapped

    graph = StateGraph(AgentState)

    graph.add_node("validate_request", _bind(node_validate_request))
    graph.add_node("query_customer_db", _bind(node_query_customer_db))
    graph.add_node("check_refund_eligibility", _bind(node_check_refund_eligibility))
    graph.add_node("escalate_to_human", _bind(node_escalate_to_human))
    graph.add_node("generate_response", _bind(node_generate_response))
    graph.add_node("log_run", _bind(node_log_run))

    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "query_customer_db")
    graph.add_edge("query_customer_db", "check_refund_eligibility")
    graph.add_conditional_edges("check_refund_eligibility", _route_after_policy)
    graph.add_edge("escalate_to_human", "generate_response")
    graph.add_edge("generate_response", "log_run")
    graph.add_edge("log_run", END)

    return graph.compile()


async def run_agent(
    *,
    conversation_id: str,
    customer_id: str,
    order_id: str,
    message: str,
    conversation_history: list[dict[str, Any]],
    request_id: str,
    task_id: str,
    agent_start_ms: float = 0.0,
    db: AsyncSession,
    config: PipelineConfig,
) -> AgentState:
    """Run agent graph end-to-end, return final state."""
    compiled = build_graph(db, config)
    initial: AgentState = {
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "current_message": message,
        "conversation_history": conversation_history,
        "customer": None,
        "policy_verdict": None,
        "decision": None,
        "request_id": request_id,
        "injection_detected": False,
        "task_id": task_id,
        "_agent_start_ms": agent_start_ms,
    }
    result: AgentState = await compiled.ainvoke(initial)
    return result
