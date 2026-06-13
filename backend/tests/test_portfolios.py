"""M7 组合 API 集成测试。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, register_user
from tests.test_backtests import _create_strategy_version, _seed_market


@pytest.mark.asyncio
async def test_portfolio_crud_and_rebalance(client):
    await _seed_market(client)
    tokens = await register_user(client, email="pf@example.com", username="pfuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)

    created = await client.post(
        "/api/v1/portfolios",
        json={
            "name": "测试组合",
            "init_capital": 500000,
            "strategy_version_id": version_id,
            "rebalance": "week",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    pid = created.json()["data"]["id"]

    detail = await client.get(f"/api/v1/portfolios/{pid}", headers=headers)
    assert detail.status_code == 200
    assert float(detail.json()["data"]["cash"]) == 500000

    reb = await client.post(f"/api/v1/portfolios/{pid}/rebalance", headers=headers)
    assert reb.status_code == 200, reb.text
    assert reb.json()["data"]["targets"]

    positions = await client.get(f"/api/v1/portfolios/{pid}/positions", headers=headers)
    assert positions.status_code == 200
    assert len(positions.json()["data"]) >= 1
