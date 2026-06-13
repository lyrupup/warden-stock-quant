"""M4 参数寻优：backtest_optimizations / results

Revision ID: 0005_init_m4_optimization
Revises: 0004_init_m4
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_init_m4_optimization"
down_revision: Union[str, None] = "0004_init_m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_optimizations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("strategy_version_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("param_space", sa.JSON(), nullable=False),
        sa.Column("method", sa.String(length=16), server_default="grid", nullable=False),
        sa.Column("objective", sa.String(length=32), server_default="sharpe", nullable=False),
        sa.Column("oos_split", sa.Numeric(4, 3), server_default="0", nullable=False),
        sa.Column("universe", sa.JSON(), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("init_capital", sa.Numeric(20, 4), nullable=False),
        sa.Column("benchmark", sa.String(length=16), server_default="000300", nullable=True),
        sa.Column("cost_config", sa.JSON(), nullable=True),
        sa.Column("adjust", sa.String(length=8), server_default="qfq", nullable=True),
        sa.Column("total_combos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("progress", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_bt_optim_user", "backtest_optimizations", ["user_id", "created_at"]
    )

    op.create_table(
        "backtest_optimization_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("optimization_id", sa.BigInteger(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("objective_value", sa.Numeric(20, 8), nullable=True),
        sa.Column("is_metrics", sa.JSON(), nullable=True),
        sa.Column("oos_metrics", sa.JSON(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["optimization_id"], ["backtest_optimizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_bt_optim_result", "backtest_optimization_results", ["optimization_id", "rank"]
    )


def downgrade() -> None:
    op.drop_index("idx_bt_optim_result", table_name="backtest_optimization_results")
    op.drop_table("backtest_optimization_results")
    op.drop_index("idx_bt_optim_user", table_name="backtest_optimizations")
    op.drop_table("backtest_optimizations")
