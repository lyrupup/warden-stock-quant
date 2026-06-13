"""M3 策略业务编排。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.features.strategies.models import Strategy, StrategyVersion
from app.features.strategies.repository import StrategyRepository
from app.features.strategies.schema import (
    StrategyUpsert,
    StrategyValidateRequest,
    StrategyValidateResult,
    StrategyVersionView,
    StrategyView,
)
from app.features.strategies.templates import list_templates
from app.features.strategies.validator import validate_config, validate_code, validate_universe


class StrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StrategyRepository(session)

    def _ensure_config_type(self, payload: StrategyUpsert) -> None:
        if payload.type == "code":
            raise ValidationFailedError("代码式策略暂未开放，请使用配置式（config）策略")

    def _validate_payload(self, payload: StrategyUpsert) -> list[str]:
        errors: list[str] = []
        if payload.type == "config":
            errors.extend(validate_config(payload.config))
        elif payload.type == "code":
            errors.extend(validate_code(payload.code))
        if payload.universe is not None:
            errors.extend(validate_universe(payload.universe.model_dump()))
        return errors

    def _universe_dict(self, payload: StrategyUpsert) -> Optional[dict[str, Any]]:
        return payload.universe.model_dump() if payload.universe else None

    async def _create_version(
        self, strategy: Strategy, payload: StrategyUpsert
    ) -> StrategyVersion:
        new_ver = strategy.latest_version + 1
        version = StrategyVersion(
            strategy_id=strategy.id,
            version=new_ver,
            params_schema=payload.params_schema,
            default_params=payload.default_params,
            config=payload.config,
            code=payload.code,
            universe=self._universe_dict(payload),
        )
        await self._repo.add_version(version)
        strategy.latest_version = new_ver
        strategy.name = payload.name
        strategy.type = payload.type
        strategy.description = payload.description
        return version

    def _to_view(self, strategy: Strategy, latest: Optional[StrategyVersion]) -> StrategyView:
        return StrategyView(
            id=strategy.id,
            name=strategy.name,
            type=strategy.type,
            description=strategy.description,
            latest_version=strategy.latest_version,
            config=latest.config if latest else None,
            code=latest.code if latest else None,
            params_schema=latest.params_schema if latest else None,
            default_params=latest.default_params if latest else None,
            universe=latest.universe if latest else None,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
        )

    async def list_strategies(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_by_user(user_id, page, size)
        items: list[dict] = []
        for s in rows:
            latest = await self._repo.get_latest_version(s.id)
            items.append(self._to_view(s, latest).model_dump())
        return items, total

    async def get_strategy(self, user_id: int, strategy_id: int) -> dict:
        strategy = await self._require_owned(strategy_id, user_id)
        latest = await self._repo.get_latest_version(strategy.id)
        return self._to_view(strategy, latest).model_dump()

    async def create_strategy(self, user_id: int, payload: StrategyUpsert) -> dict:
        self._ensure_config_type(payload)
        errors = self._validate_payload(payload)
        if errors:
            raise ValidationFailedError("策略校验失败", data={"errors": errors})

        existing = await self._repo.get_by_name(user_id, payload.name)
        if existing is not None:
            raise ConflictError("同名策略已存在")

        strategy = Strategy(
            user_id=user_id,
            name=payload.name,
            type=payload.type,
            description=payload.description,
            latest_version=0,
        )
        await self._repo.add(strategy)
        await self._create_version(strategy, payload)
        latest = await self._repo.get_latest_version(strategy.id)
        return self._to_view(strategy, latest).model_dump()

    async def update_strategy(
        self, user_id: int, strategy_id: int, payload: StrategyUpsert
    ) -> dict:
        self._ensure_config_type(payload)
        errors = self._validate_payload(payload)
        if errors:
            raise ValidationFailedError("策略校验失败", data={"errors": errors})

        strategy = await self._require_owned(strategy_id, user_id)
        if payload.name != strategy.name:
            dup = await self._repo.get_by_name(user_id, payload.name)
            if dup is not None and dup.id != strategy.id:
                raise ConflictError("同名策略已存在")

        await self._create_version(strategy, payload)
        latest = await self._repo.get_latest_version(strategy.id)
        return self._to_view(strategy, latest).model_dump()

    async def delete_strategy(self, user_id: int, strategy_id: int) -> None:
        strategy = await self._require_owned(strategy_id, user_id)
        await self._repo.delete(strategy)

    async def list_versions(self, user_id: int, strategy_id: int) -> list[dict]:
        await self._require_owned(strategy_id, user_id)
        versions = await self._repo.list_versions(strategy_id)
        return [StrategyVersionView.model_validate(v).model_dump() for v in versions]

    async def validate_strategy(
        self,
        user_id: int,
        strategy_id: int,
        payload: Optional[StrategyValidateRequest] = None,
    ) -> dict:
        strategy = await self._require_owned(strategy_id, user_id)
        latest = await self._repo.get_latest_version(strategy.id)

        stype = (payload.type if payload and payload.type else strategy.type)
        config = payload.config if payload and payload.config is not None else (
            latest.config if latest else None
        )
        code = payload.code if payload and payload.code is not None else (
            latest.code if latest else None
        )
        universe = (
            payload.universe.model_dump()
            if payload and payload.universe is not None
            else (latest.universe if latest else None)
        )

        errors: list[str] = []
        if stype == "config":
            errors.extend(validate_config(config))
        elif stype == "code":
            errors.extend(validate_code(code))
        errors.extend(validate_universe(universe))

        result = StrategyValidateResult(valid=not errors, errors=errors)
        return result.model_dump()

    async def list_templates(self) -> list[dict]:
        return [t.model_dump() for t in list_templates()]

    async def _require_owned(self, strategy_id: int, user_id: int) -> Strategy:
        strategy = await self._repo.get_owned(strategy_id, user_id)
        if strategy is not None:
            return strategy
        other = await self._repo.get_by_id_any_tenant(strategy_id)
        if other is not None:
            raise ForbiddenError("越权访问策略")
        raise NotFoundError("策略不存在")
