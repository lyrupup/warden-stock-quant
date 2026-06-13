"""M2 行情数据集 ORM（本地 market 表 + 同步作业 + 数据源凭证）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, BigIntPk, TimestampMixin


class DataSourceCredential(Base, TimestampMixin):
    """warden-stock-data 接入凭证（管理员配置，secretKey 加密存储）。"""

    __tablename__ = "data_source_credentials"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(64))
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_id: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    qps_limit: Mapped[Optional[int]] = mapped_column(Integer)
    daily_quota: Mapped[Optional[int]] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MarketSecurity(Base):
    """证券元数据。"""

    __tablename__ = "market_securities"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(64))
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="CN")
    board: Mapped[Optional[str]] = mapped_column(String(32))
    list_date: Mapped[Optional[date]] = mapped_column(Date)
    delist_date: Mapped[Optional[date]] = mapped_column(Date)
    is_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="listed")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketTradingCalendar(Base):
    """交易日历。"""

    __tablename__ = "market_trading_calendar"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MarketDailyBar(Base):
    """日 K 线（不复权 OHLC + 状态位）。"""

    __tablename__ = "market_daily_bars"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 4))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 4))
    adj_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), default=1)
    limit_up: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    limit_down: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MarketIndicatorSnapshot(Base):
    """PIT 指标快照。"""

    __tablename__ = "market_indicator_snapshots"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))


class DataSyncJob(Base):
    """数据同步作业。"""

    __tablename__ = "market_data_sync_jobs"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total: Mapped[Optional[int]] = mapped_column(Integer)
    done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    celery_job_id: Mapped[Optional[str]] = mapped_column(String(64))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SystemJob(Base):
    """异步任务统一查询表（回测/因子/同步等）。"""

    __tablename__ = "system_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_id: Mapped[Optional[int]] = mapped_column(BigIntPk)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
