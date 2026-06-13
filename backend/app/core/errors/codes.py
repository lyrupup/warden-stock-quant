"""错误码表（对应 BACKEND.md §1.5）。"""

from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    """业务错误码；与 HTTP 状态码并存。"""

    OK = 0
    BAD_REQUEST = 10001
    NOT_FOUND = 10002
    CONFLICT = 10003
    TIMEOUT = 10408
    UNAUTHORIZED = 40101
    API_KEY_INVALID = 40102
    FORBIDDEN_TENANT = 40301
    FORBIDDEN_ROLE = 40302
    LIVE_NOT_AUTHORIZED = 40303
    RATE_LIMITED = 42901
    QUOTA_EXCEEDED = 42902
    INTERNAL = 50001
    UPSTREAM_DATA = 52001
    JOB_ACCEPTED = 60001
    STRATEGY_SANDBOX = 61001
    RISK_REJECTED = 62001


# 业务错误码 -> HTTP 状态码映射。
CODE_TO_HTTP: dict[int, int] = {
    ErrorCode.OK: 200,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.TIMEOUT: 408,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.API_KEY_INVALID: 401,
    ErrorCode.FORBIDDEN_TENANT: 403,
    ErrorCode.FORBIDDEN_ROLE: 403,
    ErrorCode.LIVE_NOT_AUTHORIZED: 403,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    ErrorCode.INTERNAL: 500,
    ErrorCode.UPSTREAM_DATA: 502,
    ErrorCode.JOB_ACCEPTED: 200,
    ErrorCode.STRATEGY_SANDBOX: 422,
    ErrorCode.RISK_REJECTED: 422,
}


DEFAULT_MESSAGES: dict[int, str] = {
    ErrorCode.OK: "ok",
    ErrorCode.BAD_REQUEST: "参数错误",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.CONFLICT: "资源冲突",
    ErrorCode.TIMEOUT: "请求超时",
    ErrorCode.UNAUTHORIZED: "未认证或登录已失效",
    ErrorCode.API_KEY_INVALID: "API Key 无效或已吊销",
    ErrorCode.FORBIDDEN_TENANT: "越权访问",
    ErrorCode.FORBIDDEN_ROLE: "角色权限不足",
    ErrorCode.LIVE_NOT_AUTHORIZED: "实盘未授权",
    ErrorCode.RATE_LIMITED: "触发限流",
    ErrorCode.QUOTA_EXCEEDED: "超出配额",
    ErrorCode.INTERNAL: "服务内部错误",
    ErrorCode.UPSTREAM_DATA: "上游数据服务异常",
    ErrorCode.JOB_ACCEPTED: "任务已入队",
    ErrorCode.STRATEGY_SANDBOX: "策略校验失败",
    ErrorCode.RISK_REJECTED: "风控拦截",
}
