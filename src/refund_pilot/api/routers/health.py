"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.api.dependencies import get_db, get_settings
from refund_pilot.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — process is alive."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Readiness — DB + Redis reachable. Docker healthcheck target."""
    import redis.asyncio as aioredis

    # Check DB
    await db.execute(text("SELECT 1"))

    # Check Redis
    r = aioredis.Redis.from_url(settings.redis_url)
    await r.ping()
    await r.aclose()

    return {"status": "ok"}
