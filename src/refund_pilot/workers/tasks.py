from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, cast

from langsmith import get_current_run_tree, traceable
from loguru import logger

from refund_pilot.workers.celery_app import app


@traceable(run_type="llm", name="restate_decision")
async def _restate_decision(
    prior_run: Any,
    new_message: str,
    settings: Any,
    pipeline_config: Any,
    log: Any,
) -> dict[str, object]:
    import anthropic as _anthropic

    decision = prior_run.decision
    prior_msg = prior_run.reasoning or ""

    prompt = (
        f"You previously made a final refund decision: {decision.upper()}.\n"
        f"Reasoning: {prior_msg[:300]}\n\n"
        f'The customer is now saying: "{new_message}"\n\n'
        f"Restate your {decision} decision firmly but politely in 1-2 sentences. "
        f"Do NOT change the decision. Do NOT cite policy section numbers. "
        f"Do NOT use filler phrases. Be direct."
    )

    langsmith_run_id: str | None = None
    client: _anthropic.AsyncAnthropic | None = None
    try:
        client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        from anthropic.types import TextBlock as _TextBlock

        text_block = next((b for b in response.content if isinstance(b, _TextBlock)), None)
        text = text_block.text.strip() if text_block else ""
        token_counts = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "cache_creation": 0,
            "cache_read": 0,
        }
        rt = get_current_run_tree()
        langsmith_run_id = str(rt.id) if rt else None
    except Exception as exc:
        log.error("restate_failed", error=str(exc))
        text = (
            prior_run.reasoning[:200]
            if prior_run.reasoning
            else "Your prior request decision stands."
        )
        token_counts = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    finally:
        if client is not None:
            await client.close()

    return {
        "decision": decision,
        "run_id": str(prior_run.id),
        "customer_facing_message": text,
        "injection_detected": False,
        "input_tokens": token_counts["input"],
        "output_tokens": token_counts["output"],
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "langsmith_run_id": langsmith_run_id,
    }


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    soft_time_limit=55,
    time_limit=60,
    acks_late=True,
)
def process_refund_message(
    self: Any,
    conversation_id: str,
    customer_id: str,
    order_id: str,
    message: str,
    request_id: str,
    enqueue_time_ms: float = 0.0,
) -> dict[str, object]:
    """Process a refund message through the LangGraph agent."""
    return asyncio.run(
        _run(self, conversation_id, customer_id, order_id, message, request_id, enqueue_time_ms)
    )


async def _run(
    task: Any,
    conversation_id: str,
    customer_id: str,
    order_id: str,
    message: str,
    request_id: str,
    enqueue_time_ms: float = 0.0,
) -> dict[str, object]:
    import redis.asyncio as aioredis
    from sqlalchemy import select

    from refund_pilot.agent.graph import run_agent
    from refund_pilot.core.config import PipelineConfig, Settings
    from refund_pilot.db.models import AgentRun, ChatMessage
    from refund_pilot.db.session import AsyncSessionLocal

    settings = Settings()
    config = PipelineConfig()
    task_id: str = str(getattr(getattr(task, "request", None), "id", None) or "unknown")
    log = logger.bind(request_id=request_id, task_id=task_id, conversation_id=conversation_id)

    task_start = time.monotonic()
    e2e_start_ms: float = enqueue_time_ms if enqueue_time_ms > 0 else task_start * 1000

    async with AsyncSessionLocal() as db:
        # Idempotency: skip if task already processed
        existing = await db.execute(select(AgentRun).where(AgentRun.task_id == task_id))
        if existing.scalar_one_or_none():
            log.info("task_already_processed_skipping")
            return {"skipped": True, "task_id": task_id}

        # Short-circuit: if conversation already has a terminal decision, restate it
        prior_run_result = await db.execute(
            select(AgentRun)
            .where(AgentRun.conversation_id == uuid.UUID(conversation_id))
            .where(AgentRun.decision.in_(["approved", "denied", "escalated"]))
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        prior_run = prior_run_result.scalar_one_or_none()
        if prior_run is not None:
            restate_start_ms = time.monotonic() * 1000
            restate_result = await _restate_decision(
                prior_run=prior_run,
                new_message=message,
                settings=settings,
                pipeline_config=config,
                log=log,
            )
            latency_ms: int = int(time.monotonic() * 1000 - restate_start_ms)

            restate_run = AgentRun(
                task_id=f"restate_{task_id}",
                request_id=request_id,
                conversation_id=uuid.UUID(conversation_id),
                customer_id=uuid.UUID(customer_id),
                order_id=uuid.UUID(order_id) if order_id else None,
                input_message=message,
                decision="restate",
                reasoning=f"Restate of run {prior_run.id}: {prior_run.decision}",
                policy_clauses_cited=[],
                trace_steps=[],
                model_used=settings.claude_model,
                input_tokens=cast(int, restate_result.get("input_tokens") or 0),
                output_tokens=cast(int, restate_result.get("output_tokens") or 0),
                latency_ms=latency_ms,
                langsmith_run_id=str(restate_result.get("langsmith_run_id") or ""),
                injection_detected=False,
            )
            db.add(restate_run)

            restate_msg = ChatMessage(
                conversation_id=uuid.UUID(conversation_id),
                customer_id=uuid.UUID(customer_id),
                role="assistant",
                content=str(restate_result["customer_facing_message"]),
            )
            db.add(restate_msg)
            await db.commit()

            result_payload: dict[str, object] = {
                "task_id": task_id,
                "decision": restate_result["decision"],
                "run_id": str(restate_run.id),
                "customer_facing_message": restate_result["customer_facing_message"],
                "injection_detected": False,
                "input_tokens": restate_result["input_tokens"],
                "output_tokens": restate_result["output_tokens"],
                "cost_usd": 0.0,
                "latency_ms": latency_ms,
                "history_len": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
            }
            result_key = f"conv_result:{conversation_id}"
            async with aioredis.Redis.from_url(settings.redis_url, max_connections=1) as r:
                await r.set(result_key, json.dumps(result_payload), ex=300)
            log.info("restate_written_to_redis", key=result_key)
            return result_payload

        # Load last 10 messages for conversation history
        history_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == uuid.UUID(conversation_id))
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list(reversed(history_result.scalars().all()))
        conversation_history = [{"role": m.role, "content": m.content} for m in messages]

        history_len = len(conversation_history)
        log.info("agent_start", history_len=history_len)

        state = await run_agent(
            conversation_id=conversation_id,
            customer_id=customer_id,
            order_id=order_id,
            message=message,
            conversation_history=conversation_history,
            request_id=request_id,
            task_id=task_id,
            agent_start_ms=e2e_start_ms,
            db=db,
            config=config,
        )

        decision = state["decision"]
        customer_facing_message: str = (
            decision.customer_facing_message
            if decision
            else "Unable to process your request at this time. Please try again."
        )
        injection_detected: bool = decision.injection_detected if decision else False
        run_id: str = str(state.get("_run_id", ""))
        token_counts: dict[str, int] = state.get("_token_counts") or {
            "input": 0,
            "output": 0,
            "cache_creation": 0,
            "cache_read": 0,
        }
        input_tokens: int = token_counts.get("input", 0)
        output_tokens: int = token_counts.get("output", 0)
        cache_creation_tokens: int = token_counts.get("cache_creation", 0)
        cache_read_tokens: int = token_counts.get("cache_read", 0)
        cost_usd: float = (
            input_tokens * config.claude_input_cost_per_mtok / 1_000_000
            + output_tokens * config.claude_output_cost_per_mtok / 1_000_000
        )
        latency_ms_full: int = int(time.monotonic() * 1000 - e2e_start_ms)
        decision_str: str = decision.decision if decision else "fallback"

        log.info(
            "agent_complete",
            decision=decision_str,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost_usd, 6),
        )

        assistant_msg = ChatMessage(
            conversation_id=uuid.UUID(conversation_id),
            customer_id=uuid.UUID(customer_id),
            role="assistant",
            content=customer_facing_message,
        )
        db.add(assistant_msg)
        await db.commit()

        result_data: dict[str, object] = {
            "task_id": task_id,
            "decision": decision_str,
            "run_id": run_id,
            "customer_facing_message": customer_facing_message,
            "injection_detected": injection_detected,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms_full,
            "history_len": history_len,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_read_tokens": cache_read_tokens,
        }

        result_key = f"conv_result:{conversation_id}"
        async with aioredis.Redis.from_url(settings.redis_url, max_connections=1) as r:
            await r.set(result_key, json.dumps(result_data), ex=300)
        log.info("result_written_to_redis", key=result_key)

        return result_data
