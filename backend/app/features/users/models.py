"""M1 ORM 模型：users / api_keys / plans / quotas（对应 BACKEND.md §3.3）。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, BigIntPk, TimestampMixin


class User(Base, TimestampMixin):
    """平台用户（租户）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    live_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    quota: Mapped[Optional[Quota]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class ApiKey(Base):
    """个人 API Key：库内仅存 argon2(secret) 与可见 prefix。"""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(64))
    prefix: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[str] = mapped_column(String(128), nullable=False, default="read")
    qps_limit: Mapped[Optional[int]] = mapped_column(Integer)
    daily_quota: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="api_keys")


class Plan(Base):
    """套餐及其配额上限定义。"""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(64))
    limits: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Quota(Base):
    """用户级配额用量（M1 占位，用量逻辑后续实现）。"""

    __tablename__ = "quotas"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    usage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="quota")
