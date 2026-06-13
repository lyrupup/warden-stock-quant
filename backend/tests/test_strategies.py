"""M3 策略管理测试：CRUD、版本、校验、租户隔离。"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_header, register_user

SAMPLE_CONFIG = {
    "signals": [{"type": "ma_cross", "fast": 5, "slow": 20}],
    "rebalance": {"freq": "week"},
    "position": {"scheme": "equal_weight", "max_n": 10},
}

SAMPLE_PAYLOAD = {
    "name": "双均线测试",
    "type": "config",
    "description": "测试策略",
    "config": SAMPLE_CONFIG,
    "params_schema": {"fast": {"type": "int", "default": 5}},
    "default_params": {"fast": 5, "slow": 20},
    "universe": {"type": "all"},
}


async def _create_strategy(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {**SAMPLE_PAYLOAD, **overrides}
    resp = await client.post(
        "/api/v1/strategies",
        headers=auth_header(token),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def test_create_config_strategy(client: AsyncClient) -> None:
    user = await register_user(client)
    data = await _create_strategy(client, user["access_token"])
    assert data["id"] > 0
    assert data["latest_version"] == 1
    assert data["type"] == "config"
    assert data["config"]["signals"][0]["type"] == "ma_cross"


async def test_create_duplicate_name_conflict(client: AsyncClient) -> None:
    user = await register_user(client, email="dup@example.com", username="dup")
    await _create_strategy(client, user["access_token"], name="唯一名")
    resp = await client.post(
        "/api/v1/strategies",
        headers=auth_header(user["access_token"]),
        json={**SAMPLE_PAYLOAD, "name": "唯一名"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == 10003


async def test_reject_code_strategy(client: AsyncClient) -> None:
    user = await register_user(client, email="code@example.com", username="codeuser")
    resp = await client.post(
        "/api/v1/strategies",
        headers=auth_header(user["access_token"]),
        json={
            "name": "代码策略",
            "type": "code",
            "code": "class MyStrategy(bt.Strategy): pass",
        },
    )
    assert resp.status_code == 400
    assert "代码式" in resp.json()["message"]


async def test_list_and_get_strategy(client: AsyncClient) -> None:
    user = await register_user(client, email="list@example.com", username="listuser")
    created = await _create_strategy(client, user["access_token"])

    listing = await client.get(
        "/api/v1/strategies",
        headers=auth_header(user["access_token"]),
    )
    assert listing.status_code == 200
    body = listing.json()["data"]
    assert body["total"] == 1
    assert body["list"][0]["id"] == created["id"]

    detail = await client.get(
        f"/api/v1/strategies/{created['id']}",
        headers=auth_header(user["access_token"]),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == "双均线测试"


async def test_update_creates_new_version(client: AsyncClient) -> None:
    user = await register_user(client, email="ver@example.com", username="veruser")
    created = await _create_strategy(client, user["access_token"])

    updated_config = {
        **SAMPLE_CONFIG,
        "signals": [{"type": "ma_cross", "fast": 10, "slow": 30}],
    }
    resp = await client.put(
        f"/api/v1/strategies/{created['id']}",
        headers=auth_header(user["access_token"]),
        json={**SAMPLE_PAYLOAD, "config": updated_config},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["latest_version"] == 2
    assert data["config"]["signals"][0]["fast"] == 10

    versions = await client.get(
        f"/api/v1/strategies/{created['id']}/versions",
        headers=auth_header(user["access_token"]),
    )
    assert versions.status_code == 200
    assert len(versions.json()["data"]) == 2


async def test_validate_strategy(client: AsyncClient) -> None:
    user = await register_user(client, email="val@example.com", username="valuser")
    created = await _create_strategy(client, user["access_token"])

    ok = await client.post(
        f"/api/v1/strategies/{created['id']}/validate",
        headers=auth_header(user["access_token"]),
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["valid"] is True

    bad = await client.post(
        f"/api/v1/strategies/{created['id']}/validate",
        headers=auth_header(user["access_token"]),
        json={"config": {"signals": [{"type": "unknown"}]}},
    )
    assert bad.status_code == 200
    assert bad.json()["data"]["valid"] is False
    assert bad.json()["data"]["errors"]


async def test_invalid_config_on_create(client: AsyncClient) -> None:
    user = await register_user(client, email="bad@example.com", username="baduser")
    resp = await client.post(
        "/api/v1/strategies",
        headers=auth_header(user["access_token"]),
        json={
            **SAMPLE_PAYLOAD,
            "name": "坏策略",
            "config": {"signals": [{"type": "ma_cross", "fast": 30, "slow": 10}]},
        },
    )
    assert resp.status_code == 400
    assert resp.json()["data"]["errors"]


async def test_delete_strategy(client: AsyncClient) -> None:
    user = await register_user(client, email="del@example.com", username="deluser")
    created = await _create_strategy(client, user["access_token"])

    resp = await client.delete(
        f"/api/v1/strategies/{created['id']}",
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 200

    detail = await client.get(
        f"/api/v1/strategies/{created['id']}",
        headers=auth_header(user["access_token"]),
    )
    assert detail.status_code == 404


async def test_tenant_isolation(client: AsyncClient) -> None:
    alice = await register_user(client, email="alice@example.com", username="alice")
    bob = await register_user(client, email="bob@example.com", username="bob")
    created = await _create_strategy(client, alice["access_token"], name="Alice策略")

    resp = await client.get(
        f"/api/v1/strategies/{created['id']}",
        headers=auth_header(bob["access_token"]),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40301


async def test_list_templates(client: AsyncClient) -> None:
    user = await register_user(client, email="tpl@example.com", username="tpluser")
    resp = await client.get(
        "/api/v1/strategy-templates",
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 200
    templates = resp.json()["data"]
    assert len(templates) >= 5
    assert any(t["id"] == "ma_cross" for t in templates)
