"""M3 策略 ORM：strategies / strategy_versions。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, BigIntPk, TimestampMixin


class Strategy(Base, TimestampMixin):
    """用户策略元数据（租户隔离）。"""

    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_strategies_user_name"),)

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="config")
    description: Mapped[Optional[str]] = mapped_column(Text)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    versions: Mapped[list[StrategyVersion]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategyVersion.version",
    )


class StrategyVersion(Base):
    """策略不可变版本快照。"""

    __tablename__ = "strategy_versions"
    __table_args__ = (
        UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_ver"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    params_schema: Mapped[Optional[dict]] = mapped_column(JSON)
    default_params: Mapped[Optional[dict]] = mapped_column(JSON)
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    code: Mapped[Optional[str]] = mapped_column(Text)
    universe: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    strategy: Mapped[Strategy] = relationship(back_populates="versions")
