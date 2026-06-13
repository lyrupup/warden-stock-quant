# 守望者量化交易系统 · 后端（warden-stock-quant backend）

Python + FastAPI 实现的 A 股日线级别低频量化平台后端。本仓库当前已落地
**项目骨架 + M1（用户与多租户体系）** 的可运行最小版本。

> 权威设计文档：[`../docs/BACKEND.md`](../docs/BACKEND.md)；接口契约：[`../docs/openapi.yaml`](../docs/openapi.yaml)；需求：[`../docs/PRD.md`](../docs/PRD.md)。

## 技术栈

- FastAPI + uvicorn/gunicorn
- SQLAlchemy 2.0（async）+ Alembic
- Pydantic v2 / pydantic-settings
- Celery + Redis（任务队列，M1 仅占位）
- JWT（python-jose）+ argon2（passlib）鉴权
- structlog 结构化日志、prometheus-client 指标

> 量化重依赖（pandas / pyarrow / duckdb / backtrader / vnpy 等）将在 M2+ 里程碑按需引入，
> 当前**未安装**（见 `pyproject.toml` 注释）。

## 目录结构

```
backend/
├── app/
│   ├── main.py                # FastAPI 装配
│   ├── core/                  # 可移植核心（config/db/security/response/errors/logging/cache）
│   ├── features/              # 业务模块（M1：auth / users）
│   ├── api/                   # 路由聚合（/api/v1）
│   └── tasks/                 # Celery 应用与队列定义
├── alembic/                   # 数据库迁移
├── deploy/                    # Dockerfile + docker-compose(.dev)
├── tests/                     # pytest（M1 集成测试）
├── pyproject.toml
└── .env.example
```

## 本地开发

```bash
cd backend

# 1) 创建虚拟环境（目标 Python 3.11；若本机仅有其他 3.x 亦可，见“环境说明”）
python3 -m venv .venv && source .venv/bin/activate

# 2) 安装核心 + 开发依赖
pip install -e ".[dev]"

# 3) 配置环境变量
cp .env.example .env            # 按需修改 JWT_SECRET / PG_* / REDIS_* 等

# 4) 启动依赖（Postgres + Redis）
docker compose -f deploy/docker-compose.dev.yml up -d

# 5) 执行数据库迁移
alembic upgrade head

# 6) 启动 API（热重载）
uvicorn app.main:app --reload --port 8000

# 7)（M2+）启动 worker / beat
celery -A app.tasks.celery_app worker -Q backtest,factor,data,trade -l info
celery -A app.tasks.celery_app beat -l info
```

接口文档：启动后访问 `http://localhost:8000/docs`。

## 测试

测试使用 sqlite 内存库 + httpx ASGITransport，**无需** Postgres/Redis 即可运行：

```bash
pytest -q          # 运行 M1 测试
ruff check .       # 代码风格检查
mypy app           # 静态类型检查（可选）
```

## M1 已实现接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册（返回 JWT）|
| POST | `/api/v1/auth/login` | 登录（账号=邮箱或用户名，失败限速）|
| POST | `/api/v1/auth/refresh` | 刷新 token（轮换吊销旧 refresh）|
| POST | `/api/v1/auth/logout` | 登出（access jti 加入黑名单）|
| GET  | `/api/v1/me` | 当前用户信息与配额占位 |
| GET  | `/api/v1/api-keys` | API Key 列表（不含明文）|
| POST | `/api/v1/api-keys` | 创建 API Key（明文仅返回一次）|
| DELETE | `/api/v1/api-keys/{id}` | 吊销 API Key |
| GET  | `/healthz` | 健康检查 |
| GET  | `/metrics` | Prometheus 指标 |

鉴权支持两类 Bearer 凭证：用户 JWT 与个人 API Key（`wsq_<prefix>_<secret>`）。

## 环境说明（重要）

- **目标运行时为 Python 3.11**（见 `docs/BACKEND.md`）。当前开发机仅提供系统 Python 3.9，
  故 `pyproject.toml` 的 `requires-python` 放宽为 `>=3.9`，且 ruff/mypy 目标对齐 `py39`，
  代码均按 3.9 兼容编写。部署镜像（`deploy/Dockerfile`）仍使用 `python:3.11-slim`。
- 登录失败限速与 token 黑名单优先使用 Redis；在测试或显式指定 `DATABASE_URL`（如 sqlite）
  时自动降级为进程内内存实现，便于无 Redis 环境运行。
