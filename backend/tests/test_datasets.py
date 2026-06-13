"""HMAC 签名与数据集 API 测试。"""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from app.core.data.client import build_signature_headers


def test_build_signature_headers_structure():
    headers = build_signature_headers(
        "AKIDtest",
        "secret-key",
        "GET",
        "/open/v1/meta",
        {},
        "",
    )
    assert headers["X-Secret-Id"] == "AKIDtest"
    assert headers["X-Timestamp"].isdigit()
    assert len(headers["X-Nonce"]) >= 16
    assert headers["X-Signature"]

    body_hash = hashlib.sha256(b"").hexdigest()
    cq = ""
    sts = "\n".join(
        [
            "GET",
            "/open/v1/meta",
            cq,
            "AKIDtest",
            headers["X-Timestamp"],
            headers["X-Nonce"],
            body_hash,
        ]
    )
    expected = base64.b64encode(
        hmac.new(b"secret-key", sts.encode(), hashlib.sha256).digest()
    ).decode()
    assert headers["X-Signature"] == expected


@pytest.mark.asyncio
async def test_dataset_status_empty(client):
    from tests.conftest import auth_header, register_user

    tokens = await register_user(client)
    resp = await client.get("/api/v1/datasets/status", headers=auth_header(tokens["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["securities_count"] == 0
    assert "securities_empty" in body["data"]["gaps"]
