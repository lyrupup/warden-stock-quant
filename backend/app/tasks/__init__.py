"""Celery 任务定义（按队列：backtest / factor / data / trade）。"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
