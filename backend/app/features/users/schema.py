"""用户与 API Key 的 Pydantic DTO。"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    """当前用户信息与配额占位。"""

    id: int
    email: str
    username: Optional[str] = None
    role: str
    plan: str
    live_enabled: bool
    quota: Dict[str, object] = Field(default_factory=dict)


class ApiKeyCreate(BaseModel):
    """创建 API Key 入参。"""

    name: str
    scopes: List[str] = Field(default_factory=lambda: ["read"])


class ApiKeyCreated(BaseModel):
    """创建结果：明文 key 仅此一次返回。"""

    id: int
    name: Optional[str] = None
    prefix: str
    scopes: List[str]
    key: str


class ApiKeyView(BaseModel):
    """API Key 列表项（不含明文）。"""

    id: int
    name: Optional[str] = None
    prefix: str
    scopes: List[str]
    status: str
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
