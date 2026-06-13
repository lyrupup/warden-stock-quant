"""M10 告警 API 集成测试。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, register_user


@pytest.mark.asyncio
async def test_alert_channels_and_records(client):
    tokens = await register_user(client, email="alt@example.com", username="altuser")
    headers = auth_header(tokens["access_token"])

    created = await client.post(
        "/api/v1/alerts/channels",
        json={"type": "webhook", "config": {"url": "https://example.com/hook"}},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    channel_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/alerts/channels", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

    deleted = await client.delete(f"/api/v1/alerts/channels/{channel_id}", headers=headers)
    assert deleted.status_code == 200

    alerts = await client.get("/api/v1/alerts", headers=headers)
    assert alerts.status_code == 200
    assert "list" in alerts.json()["data"]
