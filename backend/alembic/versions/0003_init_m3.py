"""M3 初始化：strategies / strategy_versions

Revision ID: 0003_init_m3
Revises: 0002_init_m2
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_init_m3"
down_revision: Union[str, None] = "0002_init_m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=16), server_default="config", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latest_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_strategies_user_name"),
    )
    op.create_index("idx_strategies_user", "strategies", ["user_id"])

    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("params_schema", sa.JSON(), nullable=True),
        sa.Column("default_params", sa.JSON(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("universe", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_ver"),
    )
    op.create_index("idx_strategy_versions_sid", "strategy_versions", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("idx_strategy_versions_sid", table_name="strategy_versions")
    op.drop_table("strategy_versions")
    op.drop_index("idx_strategies_user", table_name="strategies")
    op.drop_table("strategies")
