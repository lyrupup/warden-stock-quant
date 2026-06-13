"""告警渠道适配与投递。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def dispatch_channel(channel_type: str, config: dict[str, Any], title: str, body: str) -> bool:
    """向指定渠道投递告警，返回是否成功。"""
    try:
        if channel_type == "webhook":
            url = config.get("url")
            if not url:
                return False
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"title": title, "body": body})
                return resp.is_success
        if channel_type == "email":
            # 首期记录日志模拟投递；生产可接 SMTP
            logger.info("alert_email", to=config.get("to"), title=title)
            return True
        if channel_type in ("dingtalk", "feishu", "serverchan"):
            url = config.get("url") or config.get("webhook")
            if url:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json={"title": title, "text": body})
                    return resp.is_success
            logger.info("alert_%s", channel_type, title=title, body=body)
            return True
    except Exception:
        logger.exception("alert_dispatch_failed", channel_type=channel_type)
    return False
