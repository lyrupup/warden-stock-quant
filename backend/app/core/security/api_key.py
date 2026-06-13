"""API Key 生成与校验：格式 wsq_<prefix>_<secret>，库内存 argon2(secret)。"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional

from passlib.context import CryptContext

_API_KEY_PREFIX = "wsq"
_PREFIX_LEN = 8
_SECRET_LEN = 32

# API Key secret 校验复用 argon2。
_key_context = CryptContext(schemes=["argon2"], deprecated="auto")


@dataclass
class ApiKeyParts:
    """API Key 的可见前缀、密钥明文与完整 key。"""

    prefix: str
    secret: str
    full_key: str


@dataclass
class ParsedApiKey:
    prefix: str
    secret: str


def generate_api_key() -> ApiKeyParts:
    """生成新的 API Key（明文仅创建时返回一次）。"""
    prefix = secrets.token_hex(_PREFIX_LEN // 2)  # 8 个 hex 字符
    secret = secrets.token_urlsafe(_SECRET_LEN)[:_SECRET_LEN]
    full_key = f"{_API_KEY_PREFIX}_{prefix}_{secret}"
    return ApiKeyParts(prefix=prefix, secret=secret, full_key=full_key)


def hash_api_secret(secret: str) -> str:
    """对 API Key secret 做 argon2 哈希存储。"""
    return _key_context.hash(secret)


def verify_api_key_secret(secret: str, hashed: str) -> bool:
    """校验 API Key secret。"""
    try:
        return _key_context.verify(secret, hashed)
    except (ValueError, TypeError):
        return False


def parse_api_key(token: str) -> Optional[ParsedApiKey]:
    """解析 wsq_<prefix>_<secret>；格式非法返回 None。"""
    if not token or not token.startswith(f"{_API_KEY_PREFIX}_"):
        return None
    parts = token.split("_", 2)
    if len(parts) != 3:
        return None
    _, prefix, secret = parts
    if not prefix or not secret:
        return None
    return ParsedApiKey(prefix=prefix, secret=secret)
