from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, cast

from langsmith import get_current_run_tree, traceable
from loguru import logger
from pydantic import BaseModel, field_validator

from refund_pilot.workers.celery_app import app

_RESTATE_CHAR_LIMIT = 80
_CONV_DECISION_TTL = 1800  # 30 min — matches tool cache TTL


_RESTATE_FALLBACK = "Your refund decision stands as previously communicated."
_RESTATE_INJECTION_MSG = (
    "Your refund decision stands. Manipulation attempts are logged "
    "and notified to our customer service team."
)


class RestateResponse(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return _RESTATE_FALLBACK
        # Trust max_tokens=80 from Claude API call — no truncation here.
        # Fallback constant is allowed to exceed 80 chars (static, not LLM output).
        return v


@traceable(run_type="llm", name="restate_decision")
async def _restate_decision(
    prior_decision: str,
    prior_reasoning: str,
    new_message: str,
    settings: Any,
    log: Any,
) -> dict[str, object]:
    import anthropic as _anthropic

    prompt = (
        f"You previously made a final refund decision: {prior_decision.upper()}.\n"
        f"Reasoning: {prior_reasoning[:300]}\n\n"
        f'The customer is now saying: "{new_message}"\n\n'
        f"Restate your {prior_decision} decision firmly but politely. "
        f"Your response MUST be {_RESTATE_CHAR_LIMIT} characters or fewer — count carefully. "
        f"Do NOT change the decision. Do NOT cite policy section numbers. "
        f"Do NOT use filler phrases. Be direct."
    )

    langsmith_run_id: str | None = None
    client: _anthropic.AsyncAnthropic | None = None
    token_counts: dict[str, int] = {"input": 0, "output": 0}
    text = f"Your refund request has been {prior_decision}. This decision is final."[
        :_RESTATE_CHAR_LIMIT
    ]
    try:
        client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=_RESTATE_CHAR_LIMIT,
            messages=[{"role": "user", "content": prompt}],
        )
        from anthropic.types import TextBlock as _TextBlock

        text_block = next((b for b in response.content if isinstance(b, _TextBlock)), None)
        raw_text = text_block.text if text_block else ""
        validated = RestateResponse(text=raw_text)
        text = validated.text
        token_counts = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
        rt = get_current_run_tree()
        langsmith_run_id = str(rt.id) if rt else None
    except Exception as exc:
        log.error("restate_failed", error=str(exc))
    finally:
        if client is not None:
            await client.close()

    return {
        "decision": prior_decision,
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

        # Short-circuit: if conversation already has a terminal decision, restate it.
        # Fix A: check Redis first (30 min TTL) before hitting DB.
        prior_decision_str: str | None = None
        prior_reasoning_str: str | None = None
        prior_run_id_str: str | None = None
        decision_cache_key = f"conv_decision:{conversation_id}"
        async with aioredis.Redis.from_url(settings.redis_url, max_connections=1) as r_check:
            cached_decision_raw = await r_check.get(decision_cache_key)
        if cached_decision_raw:
            cached_decision = json.loads(cached_decision_raw)
            prior_decision_str = cached_decision.get("decision")
            prior_reasoning_str = cached_decision.get("reasoning", "")
            prior_run_id_str = cached_decision.get("run_id")
            log.info("prior_decision_cache_hit", decision=prior_decision_str)
        else:
            prior_run_result = await db.execute(
                select(AgentRun)
                .where(AgentRun.conversation_id == uuid.UUID(conversation_id))
                .where(AgentRun.decision.in_(["approved", "denied", "escalated"]))
                .order_by(AgentRun.created_at.desc())
                .limit(1)
            )
            prior_run_obj = prior_run_result.scalar_one_or_none()
            if prior_run_obj is not None:
                prior_decision_str = prior_run_obj.decision
                prior_reasoning_str = prior_run_obj.reasoning or ""
                prior_run_id_str = str(prior_run_obj.id)

        if prior_decision_str is not None:
            from refund_pilot.agent.prompts import detect_injection

            restate_injection = detect_injection(message)
            restate_start_ms = time.monotonic() * 1000
            if restate_injection:
                log.warning("restate_injection_detected", message_preview=message[:80])
                restate_result = {
                    "decision": prior_decision_str,
                    "customer_facing_message": _RESTATE_INJECTION_MSG,
                    "injection_detected": True,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "langsmith_run_id": None,
                }
            else:
                restate_result = await _restate_decision(
                    prior_decision=prior_decision_str,
                    prior_reasoning=prior_reasoning_str or "",
                    new_message=message,
                    settings=settings,
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
                reasoning=f"Restate of run {prior_run_id_str}: {prior_decision_str}",
                policy_clauses_cited=[],
                trace_steps=[],
                model_used=settings.claude_model,
                input_tokens=cast(int, restate_result.get("input_tokens") or 0),
                output_tokens=cast(int, restate_result.get("output_tokens") or 0),
                latency_ms=latency_ms,
                langsmith_run_id=str(restate_result.get("langsmith_run_id") or ""),
                injection_detected=bool(restate_result.get("injection_detected", False)),
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
                "injection_detected": bool(restate_result.get("injection_detected", False)),
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
            # Fix A: cache terminal decision for fast restate lookup (skip DB on turn 2+)
            if decision_str in ("approved", "denied", "escalated"):
                decision_cache = json.dumps(
                    {
                        "decision": decision_str,
                        "reasoning": (decision.reasoning if decision else "")[:300],
                        "run_id": run_id,
                    }
                )
                await r.set(
                    f"conv_decision:{conversation_id}",
                    decision_cache,
                    ex=_CONV_DECISION_TTL,
                )
        log.info("result_written_to_redis", key=result_key)

        return result_data
