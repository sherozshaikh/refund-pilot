from __future__ import annotations

import time
import uuid
from typing import Any, cast

import anthropic
from anthropic.types import (
    CacheControlEphemeralParam,
    MessageParam,
    TextBlockParam,
    ToolChoiceToolParam,
)
from langsmith import get_current_run_tree, traceable
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.agent.prompts import SYSTEM_PROMPT, build_tool_schema, detect_injection
from refund_pilot.agent.state import AgentState
from refund_pilot.agent.tools import (
    PolicyVerdict,
    check_policy,
    count_recent_refunds,
    flag_escalation,
    query_customer,
    query_order,
)
from refund_pilot.core.config import PipelineConfig, Settings
from refund_pilot.core.retry import claude_retry
from refund_pilot.schemas.agent import AgentDecision, TraceStep


def _make_trace_step(
    node: str, inp: dict[str, Any], out: dict[str, Any], start_ms: float
) -> TraceStep:
    return TraceStep(
        node=node,
        input=inp,
        output=out,
        duration_ms=int(time.monotonic() * 1000 - start_ms),
    )


async def node_validate_request(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Parse and validate customer_id, order_id, detect injection."""
    start = time.monotonic() * 1000
    log = logger.bind(request_id=state["request_id"], node="validate_request")

    injection = detect_injection(state["current_message"])
    if injection:
        log.warning("injection_detected", message_preview=state["current_message"][:100])

    log.info("node_enter")
    return {
        "injection_detected": injection,
        "_trace_validate": _make_trace_step(
            "validate_request",
            {"message_len": len(state["current_message"])},
            {"injection_detected": injection},
            start,
        ),
    }


async def node_query_customer_db(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Fetch customer + order from DB."""
    start = time.monotonic() * 1000
    log = logger.bind(request_id=state["request_id"], node="query_customer_db")
    log.info("node_enter")

    customer_id = uuid.UUID(state["customer_id"])
    order_id = uuid.UUID(state["order_id"]) if state["order_id"] else None

    customer = await query_customer(customer_id, db)
    order = await query_order(order_id, db) if order_id else None
    recent_refunds = await count_recent_refunds(customer_id, db)

    log.info("db_query_done", customer_found=customer is not None, order_found=order is not None)

    return {
        "customer": customer,
        "_order": order,
        "_recent_refunds": recent_refunds,
        "_trace_query_db": _make_trace_step(
            "query_customer_db",
            {"customer_id": state["customer_id"], "order_id": state["order_id"]},
            {
                "customer_found": customer is not None,
                "order_found": order is not None,
                "recent_refunds": recent_refunds,
            },
            start,
        ),
    }


async def node_check_refund_eligibility(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Run policy check — pure function, no I/O."""
    start = time.monotonic() * 1000
    log = logger.bind(request_id=state["request_id"], node="check_refund_eligibility")
    log.info("node_enter")

    order = state.get("_order")
    recent_refunds = state.get("_recent_refunds", 0)

    if order is None:
        verdict = PolicyVerdict(
            eligible=False,
            decision="denied",
            reason="Order not found or not provided.",
            clauses=["Section 1: Order must exist to process refund"],
        )
    else:
        verdict = check_policy(order, config, recent_refunds)

    log.info("policy_verdict", decision=verdict.decision, eligible=verdict.eligible)

    return {
        "policy_verdict": verdict,
        "_trace_policy": _make_trace_step(
            "check_refund_eligibility",
            {"order_id": state["order_id"], "recent_refunds": recent_refunds},
            {"decision": verdict.decision, "clauses": verdict.clauses},
            start,
        ),
    }


@traceable(run_type="llm")
async def _call_claude(
    messages: list[MessageParam],
    client: anthropic.AsyncAnthropic,
    settings: Settings,
    config: PipelineConfig,
) -> Any:
    """Call Claude API with tool forcing and prompt caching on system prompt."""
    rt = get_current_run_tree()
    if rt:
        rt.name = settings.claude_model
    return await client.messages.create(
        model=settings.claude_model,
        max_tokens=config.claude_max_tokens,
        temperature=config.claude_temperature,
        system=[
            TextBlockParam(
                type="text",
                text=SYSTEM_PROMPT,
                cache_control=CacheControlEphemeralParam(type="ephemeral"),
            )
        ],
        tools=build_tool_schema(),
        tool_choice=ToolChoiceToolParam(type="tool", name="record_decision"),
        messages=messages,
    )


async def node_generate_response(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Call Claude API with full context — returns AgentDecision."""
    start = time.monotonic() * 1000
    settings = Settings()
    log = logger.bind(request_id=state["request_id"], node="generate_response")
    log.info("node_enter")

    verdict = state["policy_verdict"]
    assert verdict is not None, "policy_verdict must be set before generate_response"
    customer = state["customer"]
    order = state.get("_order")

    customer_info = (
        f"Customer: {customer.name}, Tier: {customer.tier}" if customer else "Customer: unknown"
    )
    order_info = (
        f"Order: {order.product_name}, Amount: ${order.amount}, "
        f"Final Sale: {order.is_final_sale}, Purchase: {order.purchase_date}"
        if order
        else "Order: not found"
    )
    policy_summary = f"Policy verdict: {verdict.decision}. Reason: {verdict.reason}"

    # Build conversation history for multi-turn context
    history = state.get("conversation_history", [])
    messages: list[MessageParam] = cast(
        list[MessageParam],
        [
            *history,
            {
                "role": "user",
                "content": (
                    f"{customer_info}\n{order_info}\n{policy_summary}\n\n"
                    f"Customer message: {state['current_message']}"
                ),
            },
        ],
    )

    from refund_pilot.agent.fallback import FallbackHandler

    decision: AgentDecision | None = None
    token_counts: dict[str, int] = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}

    # Short-circuit: injection detected by validate_request — skip Claude entirely
    if state["injection_detected"]:
        log.warning("injection_short_circuit", message_preview=state["current_message"][:80])
        return {
            "decision": AgentDecision(
                decision="denied",
                policy_clauses_cited=["Section 6.2: Policy integrity — injection attempt"],
                reasoning="Prompt injection detected by pre-filter. Claude API call skipped.",
                customer_facing_message="I can only assist with refund requests under our standard policy. Please describe your refund situation.",
                confidence=1.0,
                injection_detected=True,
            ),
            "_token_counts": token_counts,
            "_model_used": settings.claude_model,
            "_trace_generate": _make_trace_step(
                "generate_response",
                {"verdict": verdict.decision, "history_len": len(history)},
                {"decision": "denied", "injection_short_circuit": True},
                start,
            ),
        }

    client: anthropic.AsyncAnthropic | None = None
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await claude_retry(
            max_retries=config.max_retries,
            min_wait=config.retry_wait_min_seconds,
            max_wait=config.retry_wait_max_seconds,
        )(_call_claude)(messages, client, settings, config)
        tool_use = next(b for b in response.content if b.type == "tool_use")
        raw: dict[str, Any] = cast(dict[str, Any], tool_use.input)

        decision = AgentDecision(**raw)
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        log.info(
            "claude_response",
            decision=decision.decision,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        )
        token_counts = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "cache_creation": cache_creation,
            "cache_read": cache_read,
        }

    except ValidationError as exc:
        log.error(
            "claude_response_parse_failed", error=str(exc), raw=raw if "raw" in dir() else None
        )
        fallback_msg = FallbackHandler().handle(state["current_message"])
        decision = AgentDecision(
            decision="fallback",
            policy_clauses_cited=[],
            reasoning=f"Response parse failed: {exc}",
            customer_facing_message=fallback_msg
            or "We're unable to process your request right now. Please try again.",
            confidence=0.0,
            injection_detected=state["injection_detected"],
        )
    except Exception as exc:
        log.error("claude_failed_all_retries", error=str(exc))
        fallback_msg = FallbackHandler().handle(state["current_message"])
        decision = AgentDecision(
            decision="fallback",
            policy_clauses_cited=[],
            reasoning=f"Claude API unavailable: {exc}",
            customer_facing_message=fallback_msg
            or "We're unable to process your request right now. Please try again.",
            confidence=0.0,
            injection_detected=state["injection_detected"],
        )
    finally:
        if client is not None:
            await client.close()

    assert decision is not None, "decision must be set after try/except"
    return {
        "decision": decision,
        "_token_counts": token_counts,
        "_model_used": settings.claude_model,
        "_trace_generate": _make_trace_step(
            "generate_response",
            {"verdict": verdict.decision, "history_len": len(history)},
            {"decision": decision.decision, "confidence": decision.confidence},
            start,
        ),
    }


async def node_escalate_to_human(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Flag run for human review — only called when verdict=escalated."""
    start = time.monotonic() * 1000
    log = logger.bind(request_id=state["request_id"], node="escalate_to_human")
    log.info("node_enter")

    verdict = state["policy_verdict"]
    assert verdict is not None, "policy_verdict must be set before escalate_to_human"
    return {
        "_escalation_reason": verdict.reason,
        "_trace_escalate": _make_trace_step(
            "escalate_to_human",
            {"reason": verdict.reason},
            {"flagged": True},
            start,
        ),
    }


async def node_log_run(
    state: AgentState, db: AsyncSession, config: PipelineConfig
) -> dict[str, Any]:
    """Persist AgentRun record + escalation if needed. Only node with DB side effects."""
    agent_start_ms: float = state.get("_agent_start_ms", time.monotonic() * 1000)
    log = logger.bind(request_id=state["request_id"], node="log_run")
    log.info("node_enter")
    from refund_pilot.db.models import AgentRun

    decision = state["decision"]
    assert decision is not None, "decision must be set before log_run"
    token_counts: dict[str, int] = state.get("_token_counts", {"input": 0, "output": 0})

    trace_steps: list[dict[str, Any]] = []
    for step in (
        state.get("_trace_validate"),
        state.get("_trace_query_db"),
        state.get("_trace_policy"),
        state.get("_trace_escalate"),
        state.get("_trace_generate"),
    ):
        if step is not None:
            trace_steps.append(step.model_dump())

    rt = get_current_run_tree()
    langsmith_run_id = str(rt.id) if rt else None
    if rt:
        rt.extra = {
            **(rt.extra or {}),
            "decision": decision.decision,
            "injection_detected": decision.injection_detected,
        }

    run = AgentRun(
        task_id=state.get("task_id", str(uuid.uuid4())),
        request_id=state["request_id"],
        conversation_id=uuid.UUID(state["conversation_id"]),
        customer_id=uuid.UUID(state["customer_id"]),
        order_id=uuid.UUID(state["order_id"]) if state["order_id"] else None,
        input_message=state["current_message"],
        decision=decision.decision,
        reasoning=decision.reasoning,
        policy_clauses_cited=decision.policy_clauses_cited,
        trace_steps=trace_steps,
        model_used=state.get("_model_used", "unknown"),
        input_tokens=token_counts["input"],
        output_tokens=token_counts["output"],
        latency_ms=int(time.monotonic() * 1000 - agent_start_ms),
        injection_detected=decision.injection_detected,
        langsmith_run_id=langsmith_run_id,
    )
    db.add(run)
    await db.flush()  # get run.id before commit

    # Write escalation if needed
    if decision.decision == "escalated":
        reason = state.get("_escalation_reason", decision.reasoning)
        await flag_escalation(run.id, reason, db)

    await db.commit()
    log.info("run_logged", run_id=str(run.id), decision=decision.decision)

    return {"_run_id": str(run.id)}
