"""Log every request and response with structured fields."""

from __future__ import annotations

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.monotonic()
        request_id = getattr(request.state, "request_id", "-")
        logger.bind(request_id=request_id).info(
            "request_start",
            method=request.method,
            path=request.url.path,
        )
        response: Response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.bind(request_id=request_id).info(
            "request_end",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
