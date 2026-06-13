"""业务异常类型。"""

from __future__ import annotations

from typing import Optional

from app.core.errors.codes import CODE_TO_HTTP, DEFAULT_MESSAGES, ErrorCode


class BusinessError(Exception):
    """统一业务异常：携带业务码、HTTP 状态与可选数据。"""

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        http_status: Optional[int] = None,
        data: object = None,
    ) -> None:
        self.code = int(code)
        self.message = message or DEFAULT_MESSAGES.get(int(code), "error")
        self.http_status = http_status or CODE_TO_HTTP.get(int(code), 400)
        self.data = data
        super().__init__(self.message)


class ValidationFailedError(BusinessError):
    def __init__(self, message: Optional[str] = None, data: object = None) -> None:
        super().__init__(ErrorCode.BAD_REQUEST, message, data=data)


class NotFoundError(BusinessError):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(ErrorCode.NOT_FOUND, message)


class ConflictError(BusinessError):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(ErrorCode.CONFLICT, message)


class UnauthorizedError(BusinessError):
    def __init__(
        self,
        message: Optional[str] = None,
        code: ErrorCode = ErrorCode.UNAUTHORIZED,
    ) -> None:
        super().__init__(code, message)


class ForbiddenError(BusinessError):
    def __init__(
        self,
        message: Optional[str] = None,
        code: ErrorCode = ErrorCode.FORBIDDEN_TENANT,
    ) -> None:
        super().__init__(code, message)


class RateLimitedError(BusinessError):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(ErrorCode.RATE_LIMITED, message)


class QuotaExceededError(BusinessError):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(ErrorCode.QUOTA_EXCEEDED, message)
