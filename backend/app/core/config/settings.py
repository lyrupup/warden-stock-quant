"""从环境变量加载的应用配置。"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，字段名对应 .env 中的大写环境变量。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 基础
    app_env: str = "dev"
    api_port: int = 8000

    # 安全
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_access_ttl: int = 1800
    jwt_refresh_ttl: int = 604800
    jwt_algorithm: str = "HS256"
    config_enc_key: str = "dev-insecure-enc-key-change-me"

    # PostgreSQL
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "warden"
    pg_password: str = "warden"
    pg_db: str = "warden_quant"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # 数据接入（M2+）
    data_base_url: str = "http://localhost:8080"
    data_secret_id: str = ""
    data_secret_key: str = ""
    data_feed_backend: str = "auto"  # auto | pg | parquet

    # 配额默认
    max_concurrent_backtests: int = 2
    max_universe: int = 500
    max_range_days: int = 2520

    # 实盘
    live_enabled: bool = False

    # 登录失败限速
    login_fail_max: int = 5
    login_fail_window: int = 300

    # 测试 / 覆盖：显式数据库 URL（如 sqlite+aiosqlite），优先级最高
    database_url: Optional[str] = None

    # 前端公开 URL（分享链接）
    public_base_url: str = "http://localhost:5173"

    @property
    def sqlalchemy_database_uri(self) -> str:
        """异步 SQLAlchemy 连接串；存在 database_url 时优先使用。"""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    """带缓存的配置单例。"""
    return Settings()
