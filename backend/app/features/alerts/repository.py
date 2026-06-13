"""M10 告警数据访问。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alerts.models import Alert, AlertChannel


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_channels(self, user_id: int) -> list[AlertChannel]:
        rows = (
            await self._session.execute(
                select(AlertChannel)
                .where(AlertChannel.user_id == user_id)
                .order_by(AlertChannel.id.desc())
            )
        ).scalars().all()
        return list(rows)

    async def get_channel(self, channel_id: int, user_id: int) -> Optional[AlertChannel]:
        return (
            await self._session.execute(
                select(AlertChannel).where(
                    AlertChannel.id == channel_id, AlertChannel.user_id == user_id
                )
            )
        ).scalar_one_or_none()

    async def add_channel(self, channel: AlertChannel) -> AlertChannel:
        self._session.add(channel)
        await self._session.flush()
        return channel

    async def delete_channel(self, channel: AlertChannel) -> None:
        await self._session.delete(channel)

    async def list_alerts(self, user_id: int, page: int, size: int) -> tuple[list[Alert], int]:
        base = select(Alert).where(Alert.user_id == user_id).order_by(Alert.id.desc())
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await self._session.execute(base.offset((page - 1) * size).limit(size))
        ).scalars().all()
        return list(rows), int(total)

    async def add_alert(self, alert: Alert) -> Alert:
        self._session.add(alert)
        await self._session.flush()
        return alert
