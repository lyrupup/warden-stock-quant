"""FastAPI 应用装配：中间件、路由、异常处理、生命周期。

中间件装配顺序（BACKEND.md §7.5，由外到内）：
RequestID/Trace → CORS → Logging（合并于 RequestContext）→ 异常处理；
鉴权（JWT/API Key）与租户作用域以依赖注入方式在路由层实现。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api import api_router
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.response import success
from app.features.reports.service import ReportService

_logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging()
    _logger.info("app_startup", app_env=settings.app_env)
    yield
    _logger.info("app_shutdown")


def create_app() -> FastAPI:
    """应用工厂。"""
    settings = get_settings()
    app = FastAPI(
        title="守望者量化交易系统 API（Warden Stock Quant）",
        version="1.0.0",
        description="A 股日线级别低频量化研究与交易平台后端。",
        lifespan=lifespan,
    )

    # CORS（内层）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # RequestID/Trace + 访问日志（最外层，最后 add 即最先执行）
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router)

    @app.get("/share/reports/{token}", tags=["Reports"], summary="公开只读报告（分享链接）")
    async def public_shared_report(
        token: str, session: AsyncSession = Depends(get_session)
    ) -> HTMLResponse:
        html = await ReportService(session).get_shared_report_html(token)
        return HTMLResponse(content=html)

    @app.get("/healthz", tags=["System"], summary="健康检查")
    async def healthz() -> dict:
        return success({"status": "ok", "app_env": settings.app_env})

    @app.get("/metrics", tags=["System"], summary="Prometheus 指标")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
