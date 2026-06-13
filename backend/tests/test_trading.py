"""M8 仿真交易 API 测试。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, register_user
from tests.test_backtests import _create_strategy_version, _seed_market


@pytest.mark.asyncio
async def test_paper_order_and_trades(client):
    await _seed_market(client)
    tokens = await register_user(client, email="trade@example.com", username="tradeuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)

    pf = await client.post(
        "/api/v1/portfolios",
        json={"name": "交易组合", "init_capital": 500000, "strategy_version_id": version_id},
        headers=headers,
    )
    assert pf.status_code == 200, pf.text
    pid = pf.json()["data"]["id"]

    order = await client.post(
        f"/api/v1/portfolios/{pid}/orders",
        json={"code": "600000", "side": "buy", "qty": 1000, "order_type": "limit", "price": 10.5},
        headers=headers,
    )
    assert order.status_code == 200, order.text
    assert order.json()["data"]["status"] == "filled"

    orders = await client.get(f"/api/v1/portfolios/{pid}/orders", headers=headers)
    assert orders.status_code == 200
    assert len(orders.json()["data"]["list"]) >= 1

    trades = await client.get(f"/api/v1/portfolios/{pid}/trades", headers=headers)
    assert trades.status_code == 200
    assert len(trades.json()["data"]["list"]) >= 1

    positions = await client.get(f"/api/v1/portfolios/{pid}/positions", headers=headers)
    assert positions.status_code == 200
    assert len(positions.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_order_risk_rejected(client):
    await _seed_market(client)
    tokens = await register_user(client, email="rej@example.com", username="rejuser")
    headers = auth_header(tokens["access_token"])

    rs = await client.post(
        "/api/v1/risk/rule-sets",
        json={
            "name": "黑名单",
            "rules": [{"type": "blacklist", "params": {"codes": ["600000"]}, "action": "reject"}],
        },
        headers=headers,
    )
    rs_id = rs.json()["data"]["id"]

    pf = await client.post(
        "/api/v1/portfolios",
        json={
            "name": "风控组合",
            "init_capital": 100000,
            "risk_rule_set_id": rs_id,
        },
        headers=headers,
    )
    pid = pf.json()["data"]["id"]

    order = await client.post(
        f"/api/v1/portfolios/{pid}/orders",
        json={"code": "600000", "side": "buy", "qty": 100, "price": 10, "order_type": "limit"},
        headers=headers,
    )
    assert order.status_code == 422
    assert order.json()["code"] == 62001

    events = await client.get("/api/v1/risk/events", headers=headers)
    assert events.status_code == 200
    assert events.json()["data"]["total"] >= 1
