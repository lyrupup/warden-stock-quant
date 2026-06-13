"""异步引擎、会话工厂与 FastAPI 依赖。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """惰性创建并复用全局异步引擎。"""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.sqlalchemy_database_uri
        connect_args: dict = {}
        # sqlite 内存库需共享同一连接，否则各连接互不可见。
        if url.startswith("sqlite"):
            from sqlalchemy.pool import StaticPool

            connect_args = {"check_same_thread": False}
            _engine = create_async_engine(
                url,
                future=True,
                poolclass=StaticPool,
                connect_args=connect_args,
            )
        else:
            _engine = create_async_engine(url, future=True, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """惰性创建会话工厂。"""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


def reset_engine() -> None:
    """重置引擎/会话工厂（测试切换数据库时使用）。"""
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供请求作用域内的数据库会话。"""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
