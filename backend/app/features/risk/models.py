"""M9 风控 ORM。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, BigIntPk


class RiskRuleSet(Base):
    __tablename__ = "risk_rule_sets"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="portfolio")
    is_platform: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    rules: Mapped[list["RiskRule"]] = relationship(
        back_populates="rule_set", cascade="all, delete-orphan"
    )


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("risk_rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    action: Mapped[str] = mapped_column(String(16), nullable=False, default="reject")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rule_set: Mapped[RiskRuleSet] = relationship(back_populates="rules")


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portfolios.id", ondelete="SET NULL")
    )
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
