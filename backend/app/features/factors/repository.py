"""M6 因子数据访问。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.factors.models import Factor, FactorAnalysis, FactorValue


class FactorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int, page: int, size: int) -> tuple[list[Factor], int]:
        base = select(Factor).where(Factor.user_id == user_id).order_by(Factor.id.desc())
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await self._session.execute(base.offset((page - 1) * size).limit(size))
        ).scalars().all()
        return list(rows), int(total)

    async def get_owned(self, factor_id: int, user_id: int) -> Optional[Factor]:
        return (
            await self._session.execute(
                select(Factor).where(Factor.id == factor_id, Factor.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def get_by_name(self, user_id: int, name: str) -> Optional[Factor]:
        return (
            await self._session.execute(
                select(Factor).where(Factor.user_id == user_id, Factor.name == name)
            )
        ).scalar_one_or_none()

    async def add(self, factor: Factor) -> Factor:
        self._session.add(factor)
        await self._session.flush()
        return factor

    async def delete(self, factor: Factor) -> None:
        await self._session.delete(factor)

    async def save_values(
        self, factor_id: int, rows: list[tuple[str, date, Decimal]]
    ) -> None:
        await self._session.execute(delete(FactorValue).where(FactorValue.factor_id == factor_id))
        for code, trade_date, value in rows:
            self._session.add(
                FactorValue(factor_id=factor_id, code=code, trade_date=trade_date, value=value)
            )
        await self._session.flush()

    async def load_values_matrix(
        self, factor_id: int, codes: list[str], date_from: date, date_to: date
    ) -> dict[str, dict[date, float]]:
        stmt = select(FactorValue).where(
            FactorValue.factor_id == factor_id,
            FactorValue.trade_date >= date_from,
            FactorValue.trade_date <= date_to,
        )
        if codes:
            stmt = stmt.where(FactorValue.code.in_(codes))
        rows = (await self._session.execute(stmt)).scalars().all()
        out: dict[str, dict[date, float]] = {}
        for r in rows:
            out.setdefault(r.code, {})[r.trade_date] = float(r.value) if r.value else 0.0
        return out

    async def add_analysis(self, analysis: FactorAnalysis) -> FactorAnalysis:
        self._session.add(analysis)
        await self._session.flush()
        return analysis

    async def get_analysis(self, factor_id: int, analysis_id: int) -> Optional[FactorAnalysis]:
        return (
            await self._session.execute(
                select(FactorAnalysis).where(
                    FactorAnalysis.id == analysis_id, FactorAnalysis.factor_id == factor_id
                )
            )
        ).scalar_one_or_none()

    async def update_analysis(self, analysis_id: int, **values) -> None:
        row = await self._session.get(FactorAnalysis, analysis_id)
        if row is None:
            return
        for k, v in values.items():
            setattr(row, k, v)
        await self._session.flush()
