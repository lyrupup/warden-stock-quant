"""M5 报告分享 ORM。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, BigIntPk


class ReportShare(Base):
    """回测报告只读分享链接。"""

    __tablename__ = "report_shares"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
