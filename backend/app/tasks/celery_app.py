"""Celery 应用配置：broker/backend 取自环境，按队列分角色。

M1 仅做应用与队列占位；具体任务（回测/因子/数据/交易）在 M2+ 实现。
"""

from __future__ import annotations

import os

from celery import Celery
from kombu import Queue

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "warden_stock_quant",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
)

# 队列定义（与 worker -Q backtest,factor,data,trade 对应）。
celery_app.conf.task_queues = (
    Queue("backtest"),
    Queue("factor"),
    Queue("data"),
    Queue("trade"),
)
celery_app.conf.task_default_queue = "data"
celery_app.conf.timezone = "Asia/Shanghai"
celery_app.conf.task_track_started = True
celery_app.conf.worker_hijack_root_logger = False
celery_app.conf.task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in (
    "1",
    "true",
    "yes",
)
celery_app.conf.task_eager_propagates = True

# 自动加载任务模块
celery_app.autodiscover_tasks(["app.tasks"])
