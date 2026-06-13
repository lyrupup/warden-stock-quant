"""M4 回测 ORM。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, BigIntPk, TimestampMixin


class Backtest(Base, TimestampMixin):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(128))
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    universe: Mapped[Optional[dict]] = mapped_column(JSON)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    init_capital: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    benchmark: Mapped[str] = mapped_column(String(16), default="000300")
    cost_config: Mapped[Optional[dict]] = mapped_column(JSON)
    adjust: Mapped[str] = mapped_column(String(8), default="qfq")
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    job_id: Mapped[Optional[str]] = mapped_column(String(64))
    error: Mapped[Optional[str]] = mapped_column(Text)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    metric: Mapped[Optional["BacktestMetric"]] = relationship(
        back_populates="backtest", uselist=False, cascade="all, delete-orphan"
    )


class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"

    backtest_id: Mapped[int] = mapped_column(
        ForeignKey("backtests.id", ondelete="CASCADE"), primary_key=True
    )
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    annual_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    sharpe: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    sortino: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    calmar: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    mdd_from: Mapped[Optional[date]] = mapped_column(Date)
    mdd_to: Mapped[Optional[date]] = mapped_column(Date)
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    profit_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    alpha: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    info_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    extra: Mapped[Optional[dict]] = mapped_column(JSON)

    backtest: Mapped[Backtest] = relationship(back_populates="metric")


class BacktestEquity(Base):
    __tablename__ = "backtest_equity"

    backtest_id: Mapped[int] = mapped_column(
        ForeignKey("backtests.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    benchmark_nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtests.id", ondelete="CASCADE"))
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    commission: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))


class BacktestDailyPosition(Base):
    __tablename__ = "backtest_daily_positions"

    backtest_id: Mapped[int] = mapped_column(
        ForeignKey("backtests.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))


class BacktestOptimization(Base, TimestampMixin):
    """参数寻优任务（网格/随机搜索 + 批量回测）。"""

    __tablename__ = "backtest_optimizations"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(128))
    param_space: Mapped[dict] = mapped_column(JSON, nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="grid")
    objective: Mapped[str] = mapped_column(String(32), default="sharpe")
    oos_split: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0)
    universe: Mapped[Optional[dict]] = mapped_column(JSON)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    init_capital: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    benchmark: Mapped[str] = mapped_column(String(16), default="000300")
    cost_config: Mapped[Optional[dict]] = mapped_column(JSON)
    adjust: Mapped[str] = mapped_column(String(8), default="qfq")
    total_combos: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    job_id: Mapped[Optional[str]] = mapped_column(String(64))
    error: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[dict]] = mapped_column(JSON)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["BacktestOptimizationResult"]] = relationship(
        back_populates="optimization", cascade="all, delete-orphan"
    )


class BacktestOptimizationResult(Base):
    """单个参数组合的回测结果（含样本内/外指标）。"""

    __tablename__ = "backtest_optimization_results"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    optimization_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_optimizations.id", ondelete="CASCADE"), index=True
    )
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    objective_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    is_metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    oos_metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    rank: Mapped[Optional[int]] = mapped_column(Integer)

    optimization: Mapped[BacktestOptimization] = relationship(back_populates="results")
