"""M10 告警业务编排。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerting.dispatcher import dispatch_channel
from app.core.errors import NotFoundError
from app.features.alerts.models import Alert, AlertChannel
from app.features.alerts.repository import AlertRepository
from app.features.alerts.schema import AlertChannelCreate, AlertChannelView, AlertView


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AlertRepository(session)

    async def list_channels(self, user_id: int) -> list[dict]:
        rows = await self._repo.list_channels(user_id)
        return [
            AlertChannelView.model_validate(r, from_attributes=True).model_dump() for r in rows
        ]

    async def create_channel(self, user_id: int, payload: AlertChannelCreate) -> dict:
        ch = AlertChannel(
            user_id=user_id,
            type=payload.type,
            config=payload.config,
        )
        await self._repo.add_channel(ch)
        return AlertChannelView.model_validate(ch, from_attributes=True).model_dump()

    async def delete_channel(self, user_id: int, channel_id: int) -> None:
        ch = await self._repo.get_channel(channel_id, user_id)
        if ch is None:
            raise NotFoundError("告警渠道不存在")
        await self._repo.delete_channel(ch)

    async def list_alerts(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_alerts(user_id, page, size)
        items = [AlertView.model_validate(r, from_attributes=True).model_dump() for r in rows]
        return items, total

    async def emit_alert(
        self,
        user_id: int,
        title: str,
        body: str = "",
        *,
        level: str = "info",
        source: str = "system",
        dedup_key: str | None = None,
    ) -> dict:
        """落库并尝试向用户启用的渠道投递。"""
        alert = Alert(
            user_id=user_id,
            level=level,
            source=source,
            title=title,
            body=body,
            dedup_key=dedup_key,
            sent=False,
        )
        await self._repo.add_alert(alert)
        channels = [c for c in await self._repo.list_channels(user_id) if c.enabled]
        sent_any = False
        for ch in channels:
            ok = await dispatch_channel(ch.type, ch.config, title, body)
            sent_any = sent_any or ok
        alert.sent = sent_any or not channels
        await self._session.flush()
        return AlertView.model_validate(alert, from_attributes=True).model_dump()
