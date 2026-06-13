"""FastAPI 异常处理器：保证任何错误都返回统一响应结构。"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import BusinessError
from app.core.response import error

_logger = structlog.get_logger(__name__)

# HTTP 状态码 -> 业务码（用于框架抛出的 HTTPException）。
_HTTP_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN_TENANT,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.BAD_REQUEST,
    429: ErrorCode.RATE_LIMITED,
}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(BusinessError)
    async def _business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error(int(ErrorCode.BAD_REQUEST), "参数错误", exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _HTTP_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL)
        message = exc.detail if isinstance(exc.detail, str) else "请求错误"
        return JSONResponse(
            status_code=exc.status_code,
            content=error(int(code), message),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        _logger.error("unhandled_exception", error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error(int(ErrorCode.INTERNAL), "服务内部错误"),
        )
