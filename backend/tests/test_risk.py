"""M9 风控 API 与引擎测试。"""

from __future__ import annotations

import pytest

from app.core.engine.risk import OrderIntent, PositionSnapshot, RiskContext, RiskEngine, RiskRuleDef
from tests.conftest import auth_header, register_user


def test_risk_engine_max_position_pct():
    ctx = RiskContext(
        portfolio_id=1,
        user_id=1,
        cash=100000,
        total_value=1000000,
        positions=[PositionSnapshot("600000", 0, 0, 0)],
        trade_date=__import__("datetime").date(2024, 3, 1),
    )
    engine = RiskEngine(
        [RiskRuleDef(type="max_position_pct", params={"max_pct": 0.1}, action="reject")]
    )
    decision = engine.check_order(
        OrderIntent(code="600000", side="buy", qty=20000, price=10.0), ctx
    )
    assert not decision.allow


@pytest.mark.asyncio
async def test_risk_rule_set_crud(client):
    tokens = await register_user(client, email="risk@example.com", username="riskuser")
    headers = auth_header(tokens["access_token"])

    created = await client.post(
        "/api/v1/risk/rule-sets",
        json={
            "name": "默认规则",
            "scope": "portfolio",
            "rules": [
                {"type": "blacklist", "params": {"codes": ["000001"]}, "action": "reject"},
                {"type": "max_count", "params": {"max": 5}, "action": "reject"},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    rs_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/risk/rule-sets", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

    updated = await client.put(
        f"/api/v1/risk/rule-sets/{rs_id}",
        json={
            "name": "默认规则 v2",
            "scope": "portfolio",
            "rules": [{"type": "max_order_amount", "params": {"max": 100000}, "action": "reject"}],
        },
        headers=headers,
    )
    assert updated.status_code == 200

    deleted = await client.delete(f"/api/v1/risk/rule-sets/{rs_id}", headers=headers)
    assert deleted.status_code == 200
