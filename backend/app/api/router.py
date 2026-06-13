"""聚合各业务模块路由，统一挂载到 /api/v1。"""

from __future__ import annotations

from fastapi import APIRouter

from app.features.auth.router import router as auth_router
from app.features.admin.router import router as admin_router
from app.features.datasets.router import market_router, router as datasets_router
from app.features.jobs.router import router as jobs_router
from app.features.strategies.router import router as strategies_router
from app.features.backtests.router import router as backtests_router
from app.features.reports.router import router as reports_router
from app.features.factors.router import router as factors_router
from app.features.portfolios.router import router as portfolios_router
from app.features.alerts.router import router as alerts_router
from app.features.users.router import api_keys_router, me_router

api_router = APIRouter(prefix="/api/v1")

# M1：认证、当前用户、API Key。
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(api_keys_router)

# M2：数据集、行情只读、任务查询、管理员数据源。
api_router.include_router(datasets_router)
api_router.include_router(market_router)
api_router.include_router(jobs_router)
api_router.include_router(admin_router)

# M3：策略管理。
api_router.include_router(strategies_router)

# M4：回测引擎。
api_router.include_router(backtests_router)

# M5：绩效报告。
api_router.include_router(reports_router)

# M6：因子研究。
api_router.include_router(factors_router)

# M7：组合管理。
api_router.include_router(portfolios_router)

# M10：告警。
api_router.include_router(alerts_router)
