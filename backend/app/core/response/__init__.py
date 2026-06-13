"""统一响应包装 {code, message, data} 与分页结构。"""

from app.core.response.envelope import (
    ApiResponse,
    PageData,
    error,
    job_accepted,
    paginated,
    success,
)

__all__ = [
    "ApiResponse",
    "PageData",
    "error",
    "job_accepted",
    "paginated",
    "success",
]
