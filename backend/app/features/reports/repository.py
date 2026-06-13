"""M5 报告数据访问（分享链接）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reports.models import ReportShare


class ReportShareRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, share: ReportShare) -> ReportShare:
        self._session.add(share)
        await self._session.flush()
        return share

    async def get_by_token(self, token: str) -> Optional[ReportShare]:
        return (
            await self._session.execute(
                select(ReportShare).where(ReportShare.token == token)
            )
        ).scalar_one_or_none()

    async def get_valid(self, token: str, now: datetime) -> Optional[ReportShare]:
        row = await self.get_by_token(token)
        if row is None:
            return None
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            return None
        return row
