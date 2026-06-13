"""对称加密：用于 data 服务 secretKey 等敏感配置落库。"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    """由 CONFIG_ENC_KEY 派生 32 字节 Fernet 密钥。"""
    raw = get_settings().config_enc_key.encode()
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str) -> str:
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("密文解密失败") from exc
