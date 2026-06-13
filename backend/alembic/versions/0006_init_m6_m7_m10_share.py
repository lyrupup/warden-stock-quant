"""M6/M7/M10 + M5 分享链接表

Revision ID: 0006_init_m6_m7_m10_share
Revises: 0005_init_m4_optimization
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_init_m6_m7_m10_share"
down_revision: Union[str, None] = "0005_init_m4_optimization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_shares",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("backtest_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_report_shares_token", "report_shares", ["token"])

    op.create_table(
        "factors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("type", sa.String(length=16), server_default="builtin", nullable=False),
        sa.Column("expr", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("direction", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_factors_user_name"),
    )
    op.create_index("ix_factors_user_id", "factors", ["user_id"])

    op.create_table(
        "factor_values",
        sa.Column("factor_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=True),
        sa.ForeignKeyConstraint(["factor_id"], ["factors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("factor_id", "code", "trade_date"),
    )
    op.create_index("ix_factor_values_date", "factor_values", ["factor_id", "trade_date"])

    op.create_table(
        "factor_analyses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("factor_id", sa.BigInteger(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("universe", sa.JSON(), nullable=True),
        sa.Column("forward_period", sa.Integer(), server_default="5", nullable=False),
        sa.Column("n_quantiles", sa.Integer(), server_default="5", nullable=False),
        sa.Column("ic_mean", sa.Numeric(20, 8), nullable=True),
        sa.Column("ic_ir", sa.Numeric(20, 8), nullable=True),
        sa.Column("ic_win_rate", sa.Numeric(20, 8), nullable=True),
        sa.Column("quantile_returns", sa.JSON(), nullable=True),
        sa.Column("ic_series", sa.JSON(), nullable=True),
        sa.Column("turnover", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["factor_id"], ["factors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "portfolios",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=8), server_default="paper", nullable=False),
        sa.Column("strategy_version_id", sa.BigInteger(), nullable=True),
        sa.Column("init_capital", sa.Numeric(20, 4), nullable=False),
        sa.Column("cash", sa.Numeric(20, 4), nullable=False),
        sa.Column("benchmark", sa.String(length=16), server_default="000300", nullable=False),
        sa.Column("rebalance", sa.String(length=8), server_default="week", nullable=False),
        sa.Column("weight_scheme", sa.JSON(), nullable=True),
        sa.Column("risk_rule_set_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("qty", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avail_qty", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost", sa.Numeric(20, 4), nullable=True),
        sa.Column("last_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("pnl", sa.Numeric(20, 4), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "code", name="uq_positions_portfolio_code"),
    )

    op.create_table(
        "alert_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("scope", sa.String(length=16), server_default="user", nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_channels_user_id", "alert_channels", ["user_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(length=8), server_default="info", nullable=False),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.String(length=190), nullable=True),
        sa.Column("sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("alert_channels")
    op.drop_table("positions")
    op.drop_table("portfolios")
    op.drop_table("factor_analyses")
    op.drop_table("factor_values")
    op.drop_table("factors")
    op.drop_table("report_shares")
