"""统一响应封装。"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

# 异步任务受理业务码（与 app.core.errors.codes.ErrorCode.JOB_ACCEPTED 一致）。
# 此处使用字面量以避免 response 与 errors 模块的循环导入。
_JOB_ACCEPTED_CODE = 60001


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装。"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class PageData(BaseModel, Generic[T]):
    """分页数据结构。"""

    list: List[T]
    total: int
    page: int
    size: int


def success(data: Any = None, message: str = "ok", code: int = 0) -> dict:
    """构造成功响应体。"""
    return {"code": code, "message": message, "data": data}


def error(code: int, message: str, data: Any = None) -> dict:
    """构造错误响应体。"""
    return {"code": code, "message": message, "data": data}


def paginated(
    items: List[Any], total: int, page: int, size: int, message: str = "ok"
) -> dict:
    """构造分页响应体。"""
    return {
        "code": 0,
        "message": message,
        "data": {"list": items, "total": total, "page": page, "size": size},
    }


def job_accepted(resource_id: Any, job_id: str, message: str = "任务已入队") -> dict:
    """构造异步任务受理响应体（code=60001）。"""
    return {
        "code": _JOB_ACCEPTED_CODE,
        "message": message,
        "data": {"id": resource_id, "job_id": job_id},
    }
