"""M7 组合数据访问。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.portfolios.models import Portfolio, Position


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int, page: int, size: int) -> tuple[list[Portfolio], int]:
        base = select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.id.desc())
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await self._session.execute(base.offset((page - 1) * size).limit(size))
        ).scalars().all()
        return list(rows), int(total)

    async def get_owned(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        return (
            await self._session.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def get_by_name(self, user_id: int, name: str) -> Optional[Portfolio]:
        return (
            await self._session.execute(
                select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.name == name)
            )
        ).scalar_one_or_none()

    async def add(self, portfolio: Portfolio) -> Portfolio:
        self._session.add(portfolio)
        await self._session.flush()
        return portfolio

    async def delete(self, portfolio: Portfolio) -> None:
        await self._session.delete(portfolio)

    async def list_positions(self, portfolio_id: int) -> list[Position]:
        rows = (
            await self._session.execute(
                select(Position).where(Position.portfolio_id == portfolio_id).order_by(Position.code)
            )
        ).scalars().all()
        return list(rows)

    async def upsert_position(self, portfolio_id: int, code: str, **values) -> Position:
        row = (
            await self._session.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio_id, Position.code == code
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = Position(portfolio_id=portfolio_id, code=code, **values)
            self._session.add(row)
        else:
            for k, v in values.items():
                setattr(row, k, v)
        await self._session.flush()
        return row
