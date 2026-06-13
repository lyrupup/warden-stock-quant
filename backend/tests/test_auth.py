"""M1 认证测试：注册唯一性、登录限速、JWT 过期/刷新、登出。"""

from __future__ import annotations

import time

from app.core.config import get_settings
from httpx import AsyncClient
from jose import jwt

from tests.conftest import auth_header, register_user


async def test_register_success(client: AsyncClient) -> None:
    data = await register_user(client)
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


async def test_register_duplicate_email_conflict(client: AsyncClient) -> None:
    await register_user(client, email="dup@example.com", username="u1")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "username": "u2", "password": "Password123"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == 10003


async def test_register_duplicate_username_conflict(client: AsyncClient) -> None:
    await register_user(client, email="a@example.com", username="same")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "username": "same", "password": "Password123"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == 10003


async def test_register_short_password_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "short"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


async def test_login_success_with_email_and_username(client: AsyncClient) -> None:
    await register_user(client, email="login@example.com", username="loginuser")

    resp_email = await client.post(
        "/api/v1/auth/login",
        json={"account": "login@example.com", "password": "Password123"},
    )
    assert resp_email.status_code == 200
    assert resp_email.json()["data"]["access_token"]

    resp_username = await client.post(
        "/api/v1/auth/login",
        json={"account": "loginuser", "password": "Password123"},
    )
    assert resp_username.status_code == 200


async def test_login_wrong_password_unauthorized(client: AsyncClient) -> None:
    await register_user(client, email="wp@example.com", username="wp")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"account": "wp@example.com", "password": "WrongPass99"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == 40101


async def test_login_rate_limited_after_max_failures(client: AsyncClient) -> None:
    await register_user(client, email="rl@example.com", username="rl")
    settings = get_settings()

    for _ in range(settings.login_fail_max):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"account": "rl@example.com", "password": "Wrong000"},
        )
        assert resp.status_code in (401, 429)

    # 超过阈值后应触发限流 429 / 42901。
    resp = await client.post(
        "/api/v1/auth/login",
        json={"account": "rl@example.com", "password": "Wrong000"},
    )
    assert resp.status_code == 429
    assert resp.json()["code"] == 42901

    # 即使密码正确，限流期内仍被拒绝。
    resp_ok = await client.post(
        "/api/v1/auth/login",
        json={"account": "rl@example.com", "password": "Password123"},
    )
    assert resp_ok.status_code == 429


async def test_me_with_access_token(client: AsyncClient) -> None:
    data = await register_user(client, email="me@example.com", username="meuser")
    resp = await client.get("/api/v1/me", headers=auth_header(data["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["email"] == "me@example.com"
    assert body["data"]["role"] == "user"
    assert body["data"]["quota"] == {}


async def test_me_without_token_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40101


async def test_expired_access_token_rejected(client: AsyncClient) -> None:
    data = await register_user(client, email="exp@example.com", username="expuser")
    # /me 取到 user_id 以构造过期 token。
    me = await client.get("/api/v1/me", headers=auth_header(data["access_token"]))
    user_id = me.json()["data"]["id"]

    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "role": "user",
            "plan": "free",
            "type": "access",
            "jti": "expired-jti",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get("/api/v1/me", headers=auth_header(expired))
    assert resp.status_code == 401
    assert resp.json()["code"] == 40101


async def test_refresh_returns_new_tokens(client: AsyncClient) -> None:
    data = await register_user(client, email="rf@example.com", username="rfuser")
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert resp.status_code == 200
    new_data = resp.json()["data"]
    assert new_data["access_token"]
    # 新的 access token 可用。
    me = await client.get("/api/v1/me", headers=auth_header(new_data["access_token"]))
    assert me.status_code == 200


async def test_refresh_token_rotation_blacklists_old(client: AsyncClient) -> None:
    data = await register_user(client, email="rot@example.com", username="rotuser")
    first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert first.status_code == 200
    # 旧 refresh token 再次使用应失效。
    second = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert second.status_code == 401
    assert second.json()["code"] == 40101


async def test_access_token_not_accepted_as_refresh(client: AsyncClient) -> None:
    data = await register_user(client, email="ty@example.com", username="tyuser")
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["access_token"]},
    )
    assert resp.status_code == 401


async def test_logout_blacklists_access_token(client: AsyncClient) -> None:
    data = await register_user(client, email="lo@example.com", username="louser")
    headers = auth_header(data["access_token"])

    me_before = await client.get("/api/v1/me", headers=headers)
    assert me_before.status_code == 200

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200

    me_after = await client.get("/api/v1/me", headers=headers)
    assert me_after.status_code == 401
    assert me_after.json()["code"] == 40101


async def test_healthz(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
