"""冷备直导：把 warden-stock-data 的 data-export 冷备灌入本地 market 表。

上游 ``warden-stock-data/backend/data-export/`` 是 A 股全市场历史行情快照
（gzip CSV，约 1680 万行日 K）。逐只股票走 HMAC API 全量回补会非常慢，
首次构建数据集 / 大规模回补时，直接读冷备 CSV 用 PostgreSQL COPY 灌库最快。

字段在导入时映射到本项目的 market 表 schema（见 ``--help`` 与 README）。

用法（容器内，data-export 目录挂载到 /data-export）::

    python -m app.cli.import_backup --path /data-export

仅导入部分表 / 不清空旧数据::

    python -m app.cli.import_backup --path /data-export --only bars --no-truncate
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator, Optional

import asyncpg

from app.core.config import get_settings

# CSV 是 gzip 压缩 CSV，单行最大字段数远低于默认，但放宽以防异常长行。
csv.field_size_limit(10 * 1024 * 1024)


def _asyncpg_dsn() -> str:
    """从配置构造 asyncpg DSN（去掉 SQLAlchemy 的 ``+asyncpg`` 方言后缀）。"""
    s = get_settings()
    if s.database_url and s.database_url.startswith("postgresql"):
        return s.database_url.replace("+asyncpg", "")
    return (
        f"postgresql://{s.pg_user}:{s.pg_password}"
        f"@{s.pg_host}:{s.pg_port}/{s.pg_db}"
    )


def _dec(value: str) -> Optional[Decimal]:
    return Decimal(value) if value not in ("", None) else None


def _bool(value: str) -> bool:
    return value in ("t", "true", "1", "True", "TRUE")


def _date(value: str) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def _rows(path: Path) -> Iterator[list[str]]:
    """流式读取 gzip CSV，跳过表头，逐行产出原始字段列表。"""
    with gzip.open(path, "rt", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # 跳过表头
        yield from reader


def _securities_records(path: Path) -> Iterator[tuple]:
    # 冷备列：market,code,name,board,status,list_date,delist_date,is_st
    for r in _rows(path):
        yield (
            r[1],  # code
            r[2] or None,  # name
            r[0],  # market
            r[3] or None,  # board
            _date(r[5]),  # list_date
            _date(r[6]),  # delist_date
            _bool(r[7]),  # is_st
            "listed" if r[4] == "1" else "delisted",  # status
        )


def _calendar_records(path: Path) -> Iterator[tuple]:
    # 冷备列：market,cal_date,is_open,source（仅取 CN）
    seen: set[date] = set()
    for r in _rows(path):
        if r[0] != "CN":
            continue
        d = _date(r[1])
        if d is None or d in seen:
            continue
        seen.add(d)
        yield (d, _bool(r[2]))


def _bars_records(path: Path, counter: list[int]) -> Iterator[tuple]:
    # 冷备列：market,source,stock_code,trade_date,open,high,low,close,pre_close,
    #         volume,amount,turnover_rate,pct_chg,limit_up,limit_down,
    #         trade_status,is_st,adjust（价格已是前复权 qfq，故 adj_factor=1）
    for r in _rows(path):
        counter[0] += 1
        if counter[0] % 1_000_000 == 0:
            print(f"  ... 已读取日 K {counter[0]:,} 行", file=sys.stderr, flush=True)
        yield (
            r[2],  # code <- stock_code
            _date(r[3]),  # trade_date
            _dec(r[4]),  # open
            _dec(r[5]),  # high
            _dec(r[6]),  # low
            _dec(r[7]),  # close
            _dec(r[9]),  # volume
            _dec(r[10]),  # amount
            Decimal(1),  # adj_factor（冷备为 qfq 价）
            _dec(r[13]),  # limit_up
            _dec(r[14]),  # limit_down
            r[15] == "0",  # suspended <- trade_status(1 正常/0 停牌)
            _bool(r[16]),  # is_st
        )


async def _copy(
    conn: asyncpg.Connection,
    table: str,
    columns: list[str],
    records: Iterable[tuple],
    *,
    truncate: bool,
) -> int:
    if truncate:
        await conn.execute(f"TRUNCATE TABLE {table}")
    result = await conn.copy_records_to_table(table, records=records, columns=columns)
    # asyncpg 返回形如 "COPY 12345"
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


async def run(export_dir: Path, only: Optional[set[str]], truncate: bool) -> None:
    data_dir = export_dir / "data" if (export_dir / "data").is_dir() else export_dir
    targets = only or {"securities", "calendar", "bars"}

    files = {
        "securities": data_dir / "securities.csv.gz",
        "calendar": data_dir / "trading_calendars.csv.gz",
        "bars": data_dir / "stock_daily_klines.csv.gz",
    }
    for name in targets:
        if not files[name].is_file():
            raise FileNotFoundError(f"缺少冷备文件：{files[name]}")

    conn = await asyncpg.connect(_asyncpg_dsn())
    try:
        if "securities" in targets:
            print("[1/3] 导入证券列表 market_securities ...", flush=True)
            n = await _copy(
                conn,
                "market_securities",
                ["code", "name", "market", "board", "list_date", "delist_date", "is_st", "status"],
                _securities_records(files["securities"]),
                truncate=truncate,
            )
            print(f"      证券 {n:,} 条", flush=True)

        if "calendar" in targets:
            print("[2/3] 导入交易日历 market_trading_calendar ...", flush=True)
            n = await _copy(
                conn,
                "market_trading_calendar",
                ["trade_date", "is_open"],
                _calendar_records(files["calendar"]),
                truncate=truncate,
            )
            print(f"      交易日 {n:,} 条", flush=True)

        if "bars" in targets:
            print("[3/3] 导入日 K market_daily_bars（大表，约数分钟）...", flush=True)
            counter = [0]
            n = await _copy(
                conn,
                "market_daily_bars",
                [
                    "code", "trade_date", "open", "high", "low", "close",
                    "volume", "amount", "adj_factor", "limit_up", "limit_down",
                    "suspended", "is_st",
                ],
                _bars_records(files["bars"], counter),
                truncate=truncate,
            )
            print(f"      日 K {n:,} 行", flush=True)
    finally:
        await conn.close()

    print("冷备导入完成。", flush=True)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="把 warden-stock-data 的 data-export 冷备导入本地 market 表"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="data-export 目录（含 data/*.csv.gz）或其 data 子目录",
    )
    parser.add_argument(
        "--only",
        default="",
        help="仅导入指定表，逗号分隔：securities,calendar,bars（默认全部）",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="导入前不清空目标表（默认会 TRUNCATE 后全量灌入）",
    )
    args = parser.parse_args(argv)

    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    if only:
        invalid = only - {"securities", "calendar", "bars"}
        if invalid:
            parser.error(f"--only 不支持：{', '.join(sorted(invalid))}")

    asyncio.run(run(Path(args.path), only, truncate=not args.no_truncate))


if __name__ == "__main__":
    main()
