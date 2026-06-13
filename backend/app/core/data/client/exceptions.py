"""warden-stock-data 客户端异常。"""

from __future__ import annotations


class WardenDataError(Exception):
    """上游返回非零业务码或 HTTP 错误。"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
