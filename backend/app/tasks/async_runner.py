"""在 Celery 同步任务中安全运行协程（兼容 pytest-asyncio eager 模式）。"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Coroutine, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """执行协程：无运行中事件循环时用 asyncio.run，否则在新线程中运行。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
