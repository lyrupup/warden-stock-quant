"""统一业务异常、错误码与 FastAPI 异常处理器。"""

from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import (
    BusinessError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    QuotaExceededError,
    RateLimitedError,
    UnauthorizedError,
    ValidationFailedError,
)
from app.core.errors.handlers import register_exception_handlers

__all__ = [
    "ErrorCode",
    "BusinessError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "QuotaExceededError",
    "RateLimitedError",
    "UnauthorizedError",
    "ValidationFailedError",
    "register_exception_handlers",
]
