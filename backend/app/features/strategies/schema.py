"""M3 策略 API 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Universe(BaseModel):
    """股票池定义。"""

    type: Literal["all", "index", "list", "factor"] = "all"
    code: Optional[str] = None
    codes: Optional[list[str]] = None
    filter: Optional[dict[str, Any]] = None


class StrategyUpsert(BaseModel):
    """创建/更新策略（更新会生成新版本）。"""

    name: str = Field(..., min_length=1, max_length=128)
    type: Literal["config", "code"] = "config"
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    code: Optional[str] = None
    params_schema: Optional[dict[str, Any]] = None
    default_params: Optional[dict[str, Any]] = None
    universe: Optional[Universe] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class StrategyValidateRequest(BaseModel):
    """校验草稿或指定版本内容。"""

    type: Optional[Literal["config", "code"]] = None
    config: Optional[dict[str, Any]] = None
    code: Optional[str] = None
    universe: Optional[Universe] = None


class StrategyView(BaseModel):
    """策略详情视图。"""

    id: int
    name: str
    type: str
    description: Optional[str] = None
    latest_version: int
    config: Optional[dict[str, Any]] = None
    code: Optional[str] = None
    params_schema: Optional[dict[str, Any]] = None
    default_params: Optional[dict[str, Any]] = None
    universe: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyVersionView(BaseModel):
    """策略版本视图。"""

    id: int
    strategy_id: int
    version: int
    params_schema: Optional[dict[str, Any]] = None
    default_params: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    code: Optional[str] = None
    universe: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyTemplateView(BaseModel):
    """内置策略模板。"""

    id: str
    name: str
    description: str
    type: Literal["config", "code"] = "config"
    config: dict[str, Any]
    params_schema: dict[str, Any]
    default_params: dict[str, Any]
    universe: dict[str, Any]


class StrategyValidateResult(BaseModel):
    """校验结果。"""

    valid: bool
    errors: list[str] = Field(default_factory=list)
