"""安全核心：密码哈希、JWT、API Key、鉴权依赖与作用域辅助。"""

from app.core.security.api_key import (
    ApiKeyParts,
    generate_api_key,
    parse_api_key,
    verify_api_key_secret,
)
from app.core.security.deps import (
    Principal,
    get_current_principal,
    require_role,
    require_scopes,
    require_user_session,
)
from app.core.security.jwt import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security.password import hash_password, verify_password

__all__ = [
    "ApiKeyParts",
    "generate_api_key",
    "parse_api_key",
    "verify_api_key_secret",
    "Principal",
    "get_current_principal",
    "require_role",
    "require_scopes",
    "require_user_session",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
