"""M6 因子 ORM。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, BigIntPk


class Factor(Base):
    __tablename__ = "factors"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="builtin")
    expr: Mapped[Optional[str]] = mapped_column(Text)
    code: Mapped[Optional[str]] = mapped_column(Text)
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    direction: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FactorValue(Base):
    __tablename__ = "factor_values"

    factor_id: Mapped[int] = mapped_column(
        ForeignKey("factors.id", ondelete="CASCADE"), primary_key=True
    )
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))


class FactorAnalysis(Base):
    __tablename__ = "factor_analyses"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    factor_id: Mapped[int] = mapped_column(
        ForeignKey("factors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date_from: Mapped[Optional[date]] = mapped_column(Date)
    date_to: Mapped[Optional[date]] = mapped_column(Date)
    universe: Mapped[Optional[dict]] = mapped_column(JSON)
    forward_period: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    n_quantiles: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    ic_mean: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    ic_ir: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    ic_win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    quantile_returns: Mapped[Optional[dict]] = mapped_column(JSON)
    ic_series: Mapped[Optional[list]] = mapped_column(JSON)
    turnover: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    job_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
