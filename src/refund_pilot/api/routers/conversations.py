"""Conversation endpoints: create, message, stream, history."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.api.dependencies import get_db, get_pipeline_config, get_settings
from refund_pilot.core.config import PipelineConfig, Settings
from refund_pilot.core.logging import get_request_logger
from refund_pilot.core.metrics import (
    CACHE_CREATION_TOKENS,
    CACHE_READ_TOKENS,
    CONVERSATION_HISTORY_LEN,
    COST_PER_REQUEST,
    FALLBACK_USED,
    INJECTION_BY_DECISION,
    INJECTION_DETECTED,
    REFUND_COST_USD,
    REFUND_LATENCY,
    REFUND_REQUESTS,
    TOKENS_INPUT,
    TOKENS_OUTPUT,
    TOKENS_PER_REQUEST_INPUT,
    TOKENS_PER_REQUEST_OUTPUT,
)
from refund_pilot.db.models import ChatMessage, Conversation, Customer

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _record_metrics(data: dict[str, Any]) -> None:
    """Push all business metrics from a completed task result payload."""
    decision: str = data.get("decision", "fallback")
    input_tokens: int = int(data.get("input_tokens", 0))
    output_tokens: int = int(data.get("output_tokens", 0))
    cost_usd: float = float(data.get("cost_usd", 0.0))
    latency_s: float = int(data.get("latency_ms", 0)) / 1000.0
    injection: bool = bool(data.get("injection_detected", False))
    history_len: int = int(data.get("history_len", 0))

    REFUND_REQUESTS.labels(decision=decision).inc()
    REFUND_LATENCY.labels(decision=decision).observe(latency_s)

    if input_tokens > 0:
        TOKENS_INPUT.inc(input_tokens)
        TOKENS_PER_REQUEST_INPUT.observe(input_tokens)
    if output_tokens > 0:
        TOKENS_OUTPUT.inc(output_tokens)
        TOKENS_PER_REQUEST_OUTPUT.observe(output_tokens)
    if cost_usd > 0:
        REFUND_COST_USD.inc(cost_usd)
        COST_PER_REQUEST.observe(cost_usd)
    if injection:
        INJECTION_DETECTED.inc()
        INJECTION_BY_DECISION.labels(decision=decision).inc()
    if decision == "fallback":
        FALLBACK_USED.inc()
    if history_len >= 0:
        CONVERSATION_HISTORY_LEN.observe(history_len)

    cache_creation: int = int(data.get("cache_creation_tokens", 0))
    cache_read: int = int(data.get("cache_read_tokens", 0))
    if cache_creation > 0:
        CACHE_CREATION_TOKENS.inc(cache_creation)
    if cache_read > 0:
        CACHE_READ_TOKENS.inc(cache_read)


class ConversationCreateRequest(BaseModel):
    customer_id: uuid.UUID


class ConversationCreateResponse(BaseModel):
    conversation_id: str


class MessageRequest(BaseModel):
    order_id: uuid.UUID
    message: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    task_id: str


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=ConversationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationCreateResponse:
    """Open a new conversation for a customer."""
    customer = await db.get(Customer, body.customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    conv = Conversation(customer_id=body.customer_id)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationCreateResponse(conversation_id=str(conv.id))


@router.post("/{conversation_id}/message", response_model=MessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    config: PipelineConfig = Depends(get_pipeline_config),
) -> MessageResponse:
    """Enqueue refund message for async processing. Returns task_id for SSE polling."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = get_request_logger(request_id=request_id, conversation_id=str(conversation_id))

    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Per-customer rate limit via Redis sliding window
    async with aioredis.Redis.from_url(settings.redis_url) as r:
        rate_key = f"rate:{conv.customer_id}"
        current = await r.incr(rate_key)
        if current == 1:
            await r.expire(rate_key, 60)  # 1-minute window
    if current > 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    # Persist user message
    msg = ChatMessage(
        conversation_id=conversation_id,
        customer_id=conv.customer_id,
        role="user",
        content=body.message,
    )
    db.add(msg)
    await db.commit()

    # Dispatch Celery task — stamp enqueue time for E2E latency tracking
    enqueue_time_ms = time.monotonic() * 1000
    from refund_pilot.workers.tasks import process_refund_message

    task = process_refund_message.apply_async(
        kwargs={
            "conversation_id": str(conversation_id),
            "customer_id": str(conv.customer_id),
            "order_id": str(body.order_id),
            "message": body.message,
            "request_id": request_id,
            "enqueue_time_ms": enqueue_time_ms,
        },
        queue=config.celery_queue_name,
    )
    log.info("task_dispatched", task_id=task.id)
    return MessageResponse(task_id=task.id)


@router.get("/{conversation_id}/stream")
async def stream_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """SSE stream — polls Redis for task result, streams tokens to client."""

    async def event_generator() -> AsyncGenerator[str]:
        r = aioredis.Redis.from_url(settings.redis_url)
        result_key = f"conv_result:{conversation_id}"
        try:
            # Poll until result available (max 60s)
            for _ in range(60):
                if await request.is_disconnected():
                    return
                raw = await r.get(result_key)
                if raw:
                    break
                yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"
                await asyncio.sleep(1)
            else:
                from refund_pilot.core.metrics import TASK_FAILURES

                TASK_FAILURES.inc()
                yield f"data: {json.dumps({'event': 'error', 'detail': 'timeout'})}\n\n"
                return

            await r.delete(result_key)
            data = json.loads(raw)

            # Stream customer_facing_message word-by-word (~30ms/word)
            text: str = data.get("customer_facing_message", "")
            words = text.split(" ")
            for i, word in enumerate(words):
                if await request.is_disconnected():
                    return
                chunk = word if i == 0 else f" {word}"
                yield f"data: {json.dumps({'event': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            # Instrument Prometheus metrics using enriched result payload
            _record_metrics(data)

            # Final event carries decision metadata (no message text)
            yield f"data: {json.dumps({'event': 'done', 'decision': data.get('decision'), 'run_id': data.get('run_id'), 'injection_detected': data.get('injection_detected', False)})}\n\n"
        finally:
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{conversation_id}/history", response_model=list[MessageOut])
async def conversation_history(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    """Return full message thread for a conversation."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())
