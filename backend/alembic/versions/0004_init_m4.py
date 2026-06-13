"""M4 初始化：backtests / metrics / equity / trades / positions

Revision ID: 0004_init_m4
Revises: 0003_init_m3
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_init_m4"
down_revision: Union[str, None] = "0003_init_m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("strategy_version_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("universe", sa.JSON(), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("init_capital", sa.Numeric(20, 4), nullable=False),
        sa.Column("benchmark", sa.String(length=16), server_default="000300", nullable=True),
        sa.Column("cost_config", sa.JSON(), nullable=True),
        sa.Column("adjust", sa.String(length=8), server_default="qfq", nullable=True),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("progress", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_backtests_user", "backtests", ["user_id", "created_at"])

    op.create_table(
        "backtest_metrics",
        sa.Column("backtest_id", sa.BigInteger(), nullable=False),
        sa.Column("total_return", sa.Numeric(20, 8), nullable=True),
        sa.Column("annual_return", sa.Numeric(20, 8), nullable=True),
        sa.Column("volatility", sa.Numeric(20, 8), nullable=True),
        sa.Column("sharpe", sa.Numeric(20, 8), nullable=True),
        sa.Column("sortino", sa.Numeric(20, 8), nullable=True),
        sa.Column("calmar", sa.Numeric(20, 8), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(20, 8), nullable=True),
        sa.Column("mdd_from", sa.Date(), nullable=True),
        sa.Column("mdd_to", sa.Date(), nullable=True),
        sa.Column("win_rate", sa.Numeric(20, 8), nullable=True),
        sa.Column("profit_factor", sa.Numeric(20, 8), nullable=True),
        sa.Column("turnover", sa.Numeric(20, 8), nullable=True),
        sa.Column("alpha", sa.Numeric(20, 8), nullable=True),
        sa.Column("beta", sa.Numeric(20, 8), nullable=True),
        sa.Column("info_ratio", sa.Numeric(20, 8), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("backtest_id"),
    )

    op.create_table(
        "backtest_equity",
        sa.Column("backtest_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("nav", sa.Numeric(20, 8), nullable=True),
        sa.Column("benchmark_nav", sa.Numeric(20, 8), nullable=True),
        sa.Column("drawdown", sa.Numeric(20, 8), nullable=True),
        sa.Column("cash", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("backtest_id", "trade_date"),
    )

    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("backtest_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("commission", sa.Numeric(20, 4), nullable=True),
        sa.Column("tax", sa.Numeric(20, 4), nullable=True),
        sa.Column("pnl", sa.Numeric(20, 4), nullable=True),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_bt_trades", "backtest_trades", ["backtest_id", "trade_date"])

    op.create_table(
        "backtest_daily_positions",
        sa.Column("backtest_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("weight", sa.Numeric(20, 8), nullable=True),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("backtest_id", "trade_date", "code"),
    )


def downgrade() -> None:
    op.drop_table("backtest_daily_positions")
    op.drop_index("idx_bt_trades", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_equity")
    op.drop_table("backtest_metrics")
    op.drop_index("idx_backtests_user", table_name="backtests")
    op.drop_table("backtests")
