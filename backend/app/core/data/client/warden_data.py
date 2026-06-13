"""warden-stock-data 开放 API HMAC 客户端（只读）。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.core.data.client.exceptions import WardenDataError


def build_signature_headers(
    secret_id: str,
    secret_key: str,
    method: str,
    path: str,
    query: Optional[dict[str, str]] = None,
    body: str = "",
) -> dict[str, str]:
    """构造 HMAC-SHA256 签名头（对齐 API_GUIDE §3）。"""
    query = query or {}
    ts = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex
    canonical_query = "&".join(f"{k}={query[k]}" for k in sorted(query))
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    string_to_sign = "\n".join(
        [method.upper(), path, canonical_query, secret_id, ts, nonce, body_hash]
    )
    signature = base64.b64encode(
        hmac.new(secret_key.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "X-Secret-Id": secret_id,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


class WardenDataClient:
    """消费 /open/v1/* 只读行情 API。"""

    def __init__(
        self,
        base_url: str,
        secret_id: str,
        secret_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, query: Optional[dict[str, str]] = None) -> Any:
        query = query or {}
        headers = build_signature_headers(
            self._secret_id,
            self._secret_key,
            method,
            path,
            query,
        )
        url = urljoin(self._base + "/", path.lstrip("/"))
        resp = self._http.request(method, url, params=query, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        code = body.get("code")
        if code != 0:
            raise WardenDataError(int(code), str(body.get("message", "upstream error")))
        return body.get("data")

    def meta(self) -> dict:
        return self._request("GET", "/open/v1/meta")

    def securities(self, market: str = "CN") -> list[dict]:
        return self._request("GET", "/open/v1/securities", {"market": market})

    def kline(
        self,
        code: str,
        *,
        period: str = "day",
        adjust: str = "",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
        market: str = "CN",
    ) -> list[dict]:
        query: dict[str, str] = {"market": market, "period": period, "adjust": adjust}
        if date_from:
            query["from"] = date_from
        if date_to:
            query["to"] = date_to
        if limit is not None:
            query["limit"] = str(limit)
        return self._request("GET", f"/open/v1/stocks/{code}/kline", query)

    def indicators_batch(
        self,
        codes: str,
        trade_date: Optional[str] = None,
        types: str = "ma5,ma10,ma20,ma30,ma60",
        market: str = "CN",
    ) -> list[dict]:
        query: dict[str, str] = {"codes": codes, "types": types, "market": market}
        if trade_date:
            query["trade_date"] = trade_date
        return self._request("GET", "/open/v1/indicators", query)
