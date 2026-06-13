"""pytest 公共夹具：sqlite 内存库 + httpx ASGI 集成测试客户端。"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

# 必须在导入应用前设置环境变量，确保 Settings 读取测试配置。
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("JWT_ACCESS_TTL", "1800")
os.environ.setdefault("JWT_REFRESH_TTL", "604800")
os.environ.setdefault("LOGIN_FAIL_MAX", "5")
os.environ.setdefault("LOGIN_FAIL_WINDOW", "300")
os.environ.setdefault("CONFIG_ENC_KEY", "test-enc-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")

import pytest_asyncio  # noqa: E402
from app.core.cache import reset_cache  # noqa: E402
from app.core.db import session as db_session  # noqa: E402
from app.core.db.base import Base  # noqa: E402
from app.core.response import success  # noqa: E402
from app.core.security.deps import Principal, require_scopes  # noqa: E402
from app.main import app  # noqa: E402
from fastapi import Depends  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


# 仅供测试的作用域守卫路由：用于验证 API Key 越 scope 返回 403。
@app.get("/api/v1/_test/trade-only", include_in_schema=False)
async def _trade_only(
    principal: Principal = Depends(require_scopes("trade")),
) -> dict:
    return success({"ok": True, "user_id": principal.user_id})


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """每个测试一个干净的内存库与缓存。"""
    db_session.reset_engine()
    reset_cache()
    engine = db_session.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await engine.dispose()
    db_session.reset_engine()
    reset_cache()


async def register_user(
    client: AsyncClient,
    email: str = "alice@example.com",
    username: str = "alice",
    password: str = "Password123",
) -> dict:
    """注册用户并返回 token 数据。"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    return body["data"]


def auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
