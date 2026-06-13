"""M5 绩效报告 API 集成测试。"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import auth_header, register_user
from tests.test_backtests import _create_strategy_version, _seed_market


async def _create_succeeded_backtest(client, headers, version_id, name: str = "报告测试") -> int:
    start = date(2024, 1, 2)
    end = start + timedelta(days=40)
    create = await client.post(
        "/api/v1/backtests",
        json={
            "name": name,
            "strategy_version_id": version_id,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "init_capital": 1000000,
            "universe": {"type": "list", "codes": ["600000"]},
        },
        headers=headers,
    )
    assert create.status_code == 200, create.text
    return create.json()["data"]["id"]


@pytest.mark.asyncio
async def test_backtest_analysis_and_html_report(client):
    await _seed_market(client)
    tokens = await register_user(client, email="rpt@example.com", username="rptuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)
    bt_id = await _create_succeeded_backtest(client, headers, version_id)

    analysis = await client.get(f"/api/v1/backtests/{bt_id}/analysis", headers=headers)
    assert analysis.status_code == 200, analysis.text
    data = analysis.json()["data"]
    assert "monthly_returns" in data
    assert "stock_attribution" in data
    assert "benchmark_metrics" in data

    report_json = await client.get(
        f"/api/v1/backtests/{bt_id}/report", params={"format": "json"}, headers=headers
    )
    assert report_json.status_code == 200
    assert report_json.json()["data"]["metrics"]["total_return"] is not None

    report_html = await client.get(
        f"/api/v1/backtests/{bt_id}/report", params={"format": "html"}, headers=headers
    )
    assert report_html.status_code == 200
    assert "text/html" in report_html.headers.get("content-type", "")
    assert "核心绩效指标" in report_html.text


@pytest.mark.asyncio
async def test_pdf_report_and_share_link(client):
    await _seed_market(client)
    tokens = await register_user(client, email="pdf@example.com", username="pdfuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)
    bt_id = await _create_succeeded_backtest(client, headers, version_id)

    pdf = await client.get(
        f"/api/v1/backtests/{bt_id}/report", params={"format": "pdf"}, headers=headers
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"

    share = await client.post(
        f"/api/v1/backtests/{bt_id}/share",
        json={"expires_in": 3600},
        headers=headers,
    )
    assert share.status_code == 200, share.text
    token = share.json()["data"]["token"]
    assert token

    public = await client.get(f"/share/reports/{token}")
    assert public.status_code == 200
    assert "核心绩效指标" in public.text or "回测报告" in public.text


@pytest.mark.asyncio
async def test_compare_backtests(client):
    await _seed_market(client)
    tokens = await register_user(client, email="cmp@example.com", username="cmpuser")
    headers = auth_header(tokens["access_token"])
    version_id = await _create_strategy_version(client, headers)
    bt1 = await _create_succeeded_backtest(client, headers, version_id, "对比A")
    bt2 = await _create_succeeded_backtest(client, headers, version_id, "对比B")

    resp = await client.post(
        "/api/v1/reports/compare",
        json={"backtest_ids": [bt1, bt2]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    assert len(rows) == 2
    assert rows[0]["metrics"]["sharpe"] is not None
