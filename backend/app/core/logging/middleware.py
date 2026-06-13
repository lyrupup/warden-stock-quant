"""请求上下文中间件：注入 request_id / trace_id 并记录访问日志。"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

_logger = structlog.get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """为每个请求生成 request_id，并写入响应头与日志上下文。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request_id_ctx.set(request_id)
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            _logger.info("request_completed", elapsed_ms=elapsed_ms)
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response
