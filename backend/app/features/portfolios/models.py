"""M7 组合 ORM。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, BigIntPk


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False, default="paper")
    strategy_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("strategy_versions.id")
    )
    init_capital: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    benchmark: Mapped[str] = mapped_column(String(16), nullable=False, default="000300")
    rebalance: Mapped[str] = mapped_column(String(8), nullable=False, default="week")
    weight_scheme: Mapped[Optional[dict]] = mapped_column(JSON)
    risk_rule_set_id: Mapped[Optional[int]] = mapped_column(BigIntPk)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avail_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
