"""M6 因子 API 集成测试。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, register_user
from tests.test_backtests import _seed_market


async def _seed_market_two(client) -> None:
    from datetime import date, timedelta
    from decimal import Decimal
    from app.core.db import session as db_session
    from app.features.datasets.models import MarketDailyBar, MarketSecurity, MarketTradingCalendar

    sessionmaker = db_session.get_sessionmaker()
    async with sessionmaker() as session:
        for code, name in (("600000", "浦发银行"), ("600001", "邯郸钢铁")):
            session.add(MarketSecurity(code=code, name=name, market="CN", status="listed"))
        start = date(2024, 1, 2)
        for i in range(80):
            d = start + timedelta(days=i)
            session.add(MarketTradingCalendar(trade_date=d, is_open=True))
            for j, code in enumerate(("600000", "600001")):
                price = Decimal(str(10 + i * 0.3 + j))
                session.add(
                    MarketDailyBar(
                        code=code,
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


@pytest.mark.asyncio
async def test_factor_crud_and_builtin_list(client):
    await _seed_market_two(client)
    tokens = await register_user(client, email="fac@example.com", username="facuser")
    headers = auth_header(tokens["access_token"])

    listed = await client.get("/api/v1/factors", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["data"]["list"]
    assert any(i["name"] == "momentum_20" for i in items)

    created = await client.post(
        "/api/v1/factors",
        json={"name": "my_mom", "type": "expr", "expr": "momentum_20", "direction": 1},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    factor_id = created.json()["data"]["id"]

    compute = await client.post(
        f"/api/v1/factors/{factor_id}/compute",
        json={
            "universe": {"type": "list", "codes": ["600000", "600001"]},
        },
        headers=headers,
    )
    assert compute.status_code == 200, compute.text
    assert compute.json()["code"] == 60001

    analyze = await client.post(
        f"/api/v1/factors/{factor_id}/analyze",
        json={"forward_period": 5, "n_quantiles": 5},
        headers=headers,
    )
    assert analyze.status_code == 200
    aid = analyze.json()["data"]["id"]

    # eager 模式下分析应已完成
    result = await client.get(f"/api/v1/factors/{factor_id}/analyses/{aid}", headers=headers)
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["status"] == "succeeded"
    assert data["ic_mean"] is not None
