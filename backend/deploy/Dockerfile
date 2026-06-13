# 守望者量化交易系统后端镜像
# 注：目标运行时为 Python 3.11；构建上下文为 backend/ 目录。
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖：argon2-cffi 等需要构建工具与 libpq。
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖声明以利用构建缓存。
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --upgrade pip \
    && pip install .

# 拷贝其余源码（迁移脚本等）。
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# 默认以 api 角色启动；worker/beat 在 compose 中以 command 覆盖。
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000"]
