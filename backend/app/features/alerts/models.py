"""M10 告警 ORM。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, BigIntPk


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(8), nullable=False, default="info")
    source: Mapped[Optional[str]] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text)
    dedup_key: Mapped[Optional[str]] = mapped_column(String(190))
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
