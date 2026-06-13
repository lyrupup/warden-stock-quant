"""M1 租户隔离测试：越权访问他人资源返回 403。"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_header, register_user


async def test_cannot_revoke_other_users_api_key(client: AsyncClient) -> None:
    alice = await register_user(client, email="alice@example.com", username="alice")
    bob = await register_user(client, email="bob@example.com", username="bob")

    # Bob 创建一个 API Key。
    bob_key = await client.post(
        "/api/v1/api-keys",
        headers=auth_header(bob["access_token"]),
        json={"name": "bobkey", "scopes": ["read"]},
    )
    assert bob_key.status_code == 200
    bob_key_id = bob_key.json()["data"]["id"]

    # Alice 尝试吊销 Bob 的 key → 越权 403 / 40301。
    resp = await client.delete(
        f"/api/v1/api-keys/{bob_key_id}",
        headers=auth_header(alice["access_token"]),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40301


async def test_revoke_nonexistent_api_key_404(client: AsyncClient) -> None:
    alice = await register_user(client, email="a2@example.com", username="a2")
    resp = await client.delete(
        "/api/v1/api-keys/999999",
        headers=auth_header(alice["access_token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 10002


async def test_each_user_only_sees_own_api_keys(client: AsyncClient) -> None:
    alice = await register_user(client, email="a3@example.com", username="a3")
    bob = await register_user(client, email="b3@example.com", username="b3")

    await client.post(
        "/api/v1/api-keys",
        headers=auth_header(alice["access_token"]),
        json={"name": "ak", "scopes": ["read"]},
    )

    bob_list = await client.get(
        "/api/v1/api-keys", headers=auth_header(bob["access_token"])
    )
    assert bob_list.status_code == 200
    assert bob_list.json()["data"] == []
