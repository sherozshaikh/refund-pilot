"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from refund_pilot.api.middleware.logging import LoggingMiddleware
from refund_pilot.api.middleware.request_id import RequestIDMiddleware
from refund_pilot.api.routers import admin, auth, conversations, customers, health
from refund_pilot.core.config import Settings
from refund_pilot.core.logging import configure_logging
from refund_pilot.core.metrics import (  # noqa: F401 — registers metrics with Prometheus registry
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
from refund_pilot.core.telemetry import configure_telemetry


def create_app() -> FastAPI:
    """Build FastAPI app with all middleware and routers."""
    settings = Settings()
    configure_logging(settings.log_level)
    configure_telemetry()

    app = FastAPI(
        title="Refund Pilot",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware order: outermost added last (LIFO execution)
    # Execution order on request: CORS → RequestID → Logging → route
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        allow_credentials=True,
    )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # OTel FastAPI auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # Prometheus /metrics
    Instrumentator().instrument(app).expose(app)

    # Routers
    app.include_router(health.router)
    app.include_router(conversations.router)
    app.include_router(customers.router)
    app.include_router(auth.router)
    app.include_router(admin.router)

    return app


app = create_app()
