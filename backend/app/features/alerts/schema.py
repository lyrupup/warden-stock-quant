"""M10 告警 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AlertChannelCreate(BaseModel):
    type: str = Field(..., pattern="^(email|webhook|dingtalk|feishu|serverchan)$")
    config: dict[str, Any]


class AlertChannelView(AlertChannelCreate):
    id: int
    scope: str = "user"
    enabled: bool = True
    created_at: datetime


class AlertView(BaseModel):
    id: int
    level: str
    source: Optional[str] = None
    title: str
    body: Optional[str] = None
    sent: bool
    created_at: datetime
