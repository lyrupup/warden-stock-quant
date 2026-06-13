"""M1 API Key 测试：一次性明文返回、scope 校验、越 scope 403。"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_header, register_user


async def _create_key(client: AsyncClient, access_token: str, scopes: list) -> dict:
    resp = await client.post(
        "/api/v1/api-keys",
        headers=auth_header(access_token),
        json={"name": "k1", "scopes": scopes},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def test_create_api_key_returns_plaintext_once(client: AsyncClient) -> None:
    data = await register_user(client, email="ak@example.com", username="ak")
    created = await _create_key(client, data["access_token"], ["read"])
    assert created["key"].startswith("wsq_")
    assert created["prefix"] in created["key"]

    # 列表不返回明文 key。
    lst = await client.get("/api/v1/api-keys", headers=auth_header(data["access_token"]))
    assert lst.status_code == 200
    items = lst.json()["data"]
    assert len(items) == 1
    assert "key" not in items[0]
    assert items[0]["prefix"] == created["prefix"]


async def test_invalid_scope_rejected(client: AsyncClient) -> None:
    data = await register_user(client, email="iv@example.com", username="iv")
    resp = await client.post(
        "/api/v1/api-keys",
        headers=auth_header(data["access_token"]),
        json={"name": "bad", "scopes": ["read", "hack"]},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


async def test_api_key_can_access_read_endpoint(client: AsyncClient) -> None:
    data = await register_user(client, email="rd@example.com", username="rd")
    created = await _create_key(client, data["access_token"], ["read"])

    # 用 API Key 访问 /me（读）应成功。
    resp = await client.get("/api/v1/me", headers=auth_header(created["key"]))
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "rd@example.com"


async def test_api_key_scope_enforced_403(client: AsyncClient) -> None:
    data = await register_user(client, email="sc@example.com", username="sc")
    read_key = await _create_key(client, data["access_token"], ["read"])
    trade_key = await _create_key(client, data["access_token"], ["trade"])

    # read scope 访问 trade-only → 403 / 40302。
    resp_denied = await client.get(
        "/api/v1/_test/trade-only", headers=auth_header(read_key["key"])
    )
    assert resp_denied.status_code == 403
    assert resp_denied.json()["code"] == 40302

    # trade scope 可以访问。
    resp_ok = await client.get(
        "/api/v1/_test/trade-only", headers=auth_header(trade_key["key"])
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["data"]["ok"] is True


async def test_api_key_cannot_manage_api_keys(client: AsyncClient) -> None:
    data = await register_user(client, email="mg@example.com", username="mg")
    created = await _create_key(client, data["access_token"], ["read", "trade"])

    # API Key 不能用于创建/管理 API Key（需 JWT 会话）→ 403 / 40302。
    resp = await client.post(
        "/api/v1/api-keys",
        headers=auth_header(created["key"]),
        json={"name": "k2", "scopes": ["read"]},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40302


async def test_invalid_api_key_rejected(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/me", headers=auth_header("wsq_deadbeef_invalidsecretvalue")
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == 40102


async def test_revoked_api_key_rejected(client: AsyncClient) -> None:
    data = await register_user(client, email="rv@example.com", username="rv")
    created = await _create_key(client, data["access_token"], ["read"])

    delete = await client.delete(
        f"/api/v1/api-keys/{created['id']}",
        headers=auth_header(data["access_token"]),
    )
    assert delete.status_code == 200

    resp = await client.get("/api/v1/me", headers=auth_header(created["key"]))
    assert resp.status_code == 401
    assert resp.json()["code"] == 40102
