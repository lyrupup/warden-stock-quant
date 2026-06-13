"""M4 回测 API 集成测试。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tests.conftest import auth_header, register_user


async def _seed_market(client) -> None:
    """向内存库写入最小行情数据集。"""
    from app.core.db import session as db_session
    from app.features.datasets.models import MarketDailyBar, MarketSecurity, MarketTradingCalendar

    sessionmaker = db_session.get_sessionmaker()
    async with sessionmaker() as session:
        session.add(
            MarketSecurity(
                code="600000",
                name="浦发银行",
                market="CN",
                status="listed",
            )
        )
        start = date(2024, 1, 2)
        for i in range(80):
            d = start + timedelta(days=i)
            session.add(MarketTradingCalendar(trade_date=d, is_open=True))
            price = Decimal(str(10 + i * 0.3))
            session.add(
                MarketDailyBar(
                    code="600000",
                    trade_date=d,
                    open=price,
                    high=price + Decimal("0.5"),
                    low=price - Decimal("0.5"),
                    close=price,
                    volume=Decimal("1000000"),
                    amount=Decimal("10000000"),
                    adj_factor=Decimal("1"),
                    suspended=False,
                )
            )
        await session.commit()


async def _create_strategy_version(client, headers: dict) -> int:
    payload = {
        "name": "测试双均线",
        "type": "config",
        "config": {
            "signals": [{"type": "ma_cross", "fast": 5, "slow": 10}],
            "rebalance": {"freq": "day"},
            "position": {"scheme": "equal_weight", "max_n": 1},
        },
        # 策略默认股票池为全市场；回测创建时会覆盖为指定列表
        "universe": {"type": "all"},
    }
    resp = await client.post("/api/v1/strategies", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    strategy_id = resp.json()["data"]["id"]
    ver_resp = await client.get(f"/api/v1/strategies/{strategy_id}/versions", headers=headers)
    versions = ver_resp.json()["data"]
    return versions[0]["id"]


@pytest.mark.asyncio
async def test_create_backtest_and_get_results(client):
    await _seed_market(client)
    tokens = await register_user(client, email="bt@example.com", username="btuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)

    start = date(2024, 1, 2)
    end = start + timedelta(days=40)
    create = await client.post(
        "/api/v1/backtests",
        json={
            "strategy_version_id": version_id,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "init_capital": 1000000,
            "universe": {"type": "list", "codes": ["600000"]},
        },
        headers=headers,
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["code"] == 60001
    bt_id = body["data"]["id"]

    detail = await client.get(f"/api/v1/backtests/{bt_id}", headers=headers)
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["status"] == "succeeded"
    # 详情/列表应回显关联策略名与可读版本号
    assert detail_data["strategy_name"] == "测试双均线"
    assert detail_data["strategy_version"] == 1
    assert detail_data["strategy_id"] is not None

    listed = await client.get("/api/v1/backtests", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["list"][0]["strategy_name"] == "测试双均线"

    # 策略快照接口返回当时绑定的配置
    snap = await client.get(f"/api/v1/backtests/{bt_id}/strategy", headers=headers)
    assert snap.status_code == 200
    snap_data = snap.json()["data"]
    assert snap_data["version"] == 1
    assert snap_data["strategy_name"] == "测试双均线"
    assert snap_data["config"]["signals"][0]["type"] == "ma_cross"
    # 股票池应反映本次回测实际选择（list），而非策略默认（all）
    assert snap_data["universe"]["type"] == "list"
    assert snap_data["universe"]["codes"] == ["600000"]

    metrics = await client.get(f"/api/v1/backtests/{bt_id}/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["data"]["total_return"] is not None

    equity = await client.get(f"/api/v1/backtests/{bt_id}/equity", headers=headers)
    assert equity.status_code == 200
    assert len(equity.json()["data"]) > 0


@pytest.mark.asyncio
async def test_backtest_tenant_isolation(client):
    await _seed_market(client)
    tokens_a = await register_user(client, email="a@bt.com", username="auser")
    tokens_b = await register_user(client, email="b@bt.com", username="buser")
    headers_a = auth_header(tokens_a["access_token"])
    version_id = await _create_strategy_version(client, headers_a)

    start = date(2024, 1, 2)
    end = start + timedelta(days=20)
    create = await client.post(
        "/api/v1/backtests",
        json={
            "strategy_version_id": version_id,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "init_capital": 500000,
            "universe": {"type": "list", "codes": ["600000"]},
        },
        headers=headers_a,
    )
    bt_id = create.json()["data"]["id"]
    headers_b = auth_header(tokens_b["access_token"])
    resp = await client.get(f"/api/v1/backtests/{bt_id}", headers=headers_b)
    assert resp.status_code == 404
