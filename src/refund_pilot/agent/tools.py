"""Tool functions: query_customer, query_order, check_policy, flag_escalation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date
from types import SimpleNamespace
from typing import Any, cast

import redis.asyncio as aioredis
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.core.config import PipelineConfig, Settings
from refund_pilot.core.retry import db_retry
from refund_pilot.db.models import AgentRun, Customer, Escalation, Order

_settings = Settings()


async def _cache_get(key: str) -> dict[str, Any] | None:
    try:
        async with aioredis.Redis.from_url(_settings.redis_url, max_connections=1) as r:
            val = await r.get(key)
            return cast(dict[str, Any], json.loads(val)) if val else None
    except Exception:
        return None


async def _cache_set(key: str, data: dict[str, Any], ttl: int) -> None:
    try:
        async with aioredis.Redis.from_url(_settings.redis_url, max_connections=1) as r:
            await r.setex(key, ttl, json.dumps(data, default=str))
    except Exception:
        pass


class PolicyVerdict:
    """Result of check_policy — not a Pydantic model, internal only."""

    __slots__ = ("eligible", "decision", "reason", "clauses")

    def __init__(self, eligible: bool, decision: str, reason: str, clauses: list[str]) -> None:
        self.eligible = eligible
        self.decision = decision
        self.reason = reason
        self.clauses = clauses


@db_retry()
async def query_customer(customer_id: uuid.UUID, db: AsyncSession) -> Customer | None:
    """Return Customer or None. Cache hit returns SimpleNamespace with same attributes."""
    config = PipelineConfig()
    cache_key = f"tool_cache:customer:{customer_id}"
    cached = await _cache_get(cache_key)
    if cached:
        logger.debug("customer_cache_hit", customer_id=str(customer_id))
        return cast(
            Customer,
            SimpleNamespace(
                id=uuid.UUID(cached["id"]),
                name=cached["name"],
                email=cached["email"],
                tier=cached["tier"],
            ),
        )
    result = await db.get(Customer, customer_id)
    if result:
        await _cache_set(
            cache_key,
            {
                "id": str(result.id),
                "name": result.name,
                "email": result.email,
                "tier": result.tier,
            },
            config.tool_cache_ttl_seconds,
        )
    return result


@db_retry()
async def query_order(order_id: uuid.UUID, db: AsyncSession) -> Order | None:
    """Return Order or None. Immutable fields cached; status included with short-lived TTL."""
    config = PipelineConfig()
    cache_key = f"tool_cache:order:{order_id}"
    cached = await _cache_get(cache_key)
    if cached:
        logger.debug("order_cache_hit", order_id=str(order_id))
        return cast(
            Order,
            SimpleNamespace(
                id=uuid.UUID(cached["id"]),
                customer_id=uuid.UUID(cached["customer_id"]),
                product_name=cached["product_name"],
                amount=float(cached["amount"]),
                is_final_sale=cached["is_final_sale"],
                purchase_date=date.fromisoformat(cached["purchase_date"]),
                category=cached["category"],
                status=cached["status"],
            ),
        )
    result = await db.get(Order, order_id)
    if result:
        await _cache_set(
            cache_key,
            {
                "id": str(result.id),
                "customer_id": str(result.customer_id),
                "product_name": result.product_name,
                "amount": float(result.amount),
                "is_final_sale": result.is_final_sale,
                "purchase_date": result.purchase_date.isoformat(),
                "category": result.category,
                "status": result.status,
            },
            config.tool_cache_ttl_seconds,
        )
    return result


@db_retry()
async def count_recent_refunds(customer_id: uuid.UUID, db: AsyncSession) -> int:
    """Return number of approved/escalated agent_runs for customer in last 30 days."""
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=30)
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.customer_id == customer_id,
            AgentRun.decision.in_(["approved", "escalated"]),
            AgentRun.created_at >= cutoff,
        )
    )
    return len(result.scalars().all())


def check_policy(
    order: Order,
    config: PipelineConfig,
    recent_refunds: int = 0,
    today: date | None = None,
) -> PolicyVerdict:
    """Evaluate order against refund policy rules. Pure — no DB, no I/O."""
    today = today or date.today()
    days_since_purchase = (today - order.purchase_date).days

    # Section 5: fraud indicator — multiple refunds
    if recent_refunds >= 3:
        return PolicyVerdict(
            eligible=False,
            decision="escalated",
            reason=f"Customer has {recent_refunds} refund requests in the last 30 days.",
            clauses=["Section 5.1: Multiple refund requests require escalation"],
        )

    # Section 2: final sale — hard deny, no exceptions
    if order.is_final_sale:
        return PolicyVerdict(
            eligible=False,
            decision="denied",
            reason="Item is marked as final sale and is not eligible for refund.",
            clauses=[
                "Section 2.1: Final sale items are not eligible for refund or return",
                "Section 2.3: Final sale designation cannot be waived",
            ],
        )

    # Section 1: outside 30-day window
    if days_since_purchase > config.refund_window_days:
        return PolicyVerdict(
            eligible=False,
            decision="denied",
            reason=f"Purchase was {days_since_purchase} days ago, outside the {config.refund_window_days}-day window.",
            clauses=[
                "Section 1.1: Refund requests must be submitted within 30 days of purchase",
                "Section 1.3: No exceptions to the 30-day window",
            ],
        )

    # Section 3: high-value — must escalate
    if float(order.amount) > config.escalation_threshold_usd:
        return PolicyVerdict(
            eligible=False,
            decision="escalated",
            reason=f"Order amount ${order.amount} exceeds escalation threshold of ${config.escalation_threshold_usd}.",
            clauses=[
                "Section 3.1: Refund requests exceeding $500 must be escalated",
                "Section 3.2: Agent must not approve or deny — escalation mandatory",
            ],
        )

    # Eligible
    return PolicyVerdict(
        eligible=True,
        decision="approved",
        reason="Order meets all refund eligibility criteria.",
        clauses=["Section 1.1: Within 30-day window", "Section 4.1: Eligible for refund"],
    )


@db_retry()
async def flag_escalation(agent_run_id: uuid.UUID, reason: str, db: AsyncSession) -> None:
    """Insert escalation record for human review."""
    db.add(Escalation(agent_run_id=agent_run_id, reason=reason))
    await db.commit()
    logger.info("escalation_flagged", agent_run_id=str(agent_run_id), reason=reason)
