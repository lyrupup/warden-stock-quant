"""M5 绩效报告业务编排。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine.report.analysis import build_report_analysis
from app.core.engine.report.html_renderer import render_html_report
from app.core.errors import NotFoundError, ValidationFailedError
from app.features.backtests.repository import BacktestRepository
from app.features.backtests.schema import BacktestMetricsView, BacktestView
from app.features.backtests.service import BacktestService
from app.features.reports.schema import (
    BacktestReportView,
    BenchmarkMetricsView,
    CompareBacktestsRequest,
    CompareReportView,
    CompareRowView,
    ReportAnalysisView,
)
from app.features.strategies.repository import StrategyRepository


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bt_repo = BacktestRepository(session)
        self._bt_service = BacktestService(session)
        self._strategy_repo = StrategyRepository(session)

    async def get_analysis(self, user_id: int, backtest_id: int) -> ReportAnalysisView:
        await self._require_succeeded(user_id, backtest_id)
        raw = await self._load_raw_series(backtest_id)
        analysis = build_report_analysis(raw["equity"], raw["trades"], raw["positions"])
        return ReportAnalysisView.model_validate(analysis)

    async def get_report(self, user_id: int, backtest_id: int) -> BacktestReportView:
        bt_view = await self._bt_service.get_backtest(user_id, backtest_id)
        if bt_view.status != "succeeded":
            raise ValidationFailedError("仅已完成的回测可生成报告")
        metrics = await self._bt_service.get_metrics(user_id, backtest_id)
        analysis = await self.get_analysis(user_id, backtest_id)
        return BacktestReportView(backtest=bt_view, metrics=metrics, analysis=analysis)

    async def render_html(self, user_id: int, backtest_id: int) -> str:
        report = await self.get_report(user_id, backtest_id)
        bt = report.backtest
        m = report.metrics
        a = report.analysis

        def _tone_pct(v: Optional[Any], invert: bool = False) -> str:
            if v is None:
                return ""
            try:
                n = float(v)
            except (TypeError, ValueError):
                return ""
            pos = n >= 0 if not invert else n <= 0
            return "pos" if pos else "neg"

        metric_cards = [
            {"label": "总收益率", "value": _fmt_pct(m.total_return), "tone": _tone_pct(m.total_return)},
            {"label": "年化收益", "value": _fmt_pct(m.annual_return), "tone": _tone_pct(m.annual_return)},
            {"label": "最大回撤", "value": _fmt_pct(m.max_drawdown), "tone": "neg"},
            {"label": "夏普比率", "value": _fmt_num(m.sharpe), "tone": ""},
            {"label": "索提诺比率", "value": _fmt_num(m.sortino), "tone": ""},
            {"label": "卡玛比率", "value": _fmt_num(m.calmar), "tone": ""},
            {"label": "年化波动", "value": _fmt_pct(m.volatility), "tone": ""},
            {"label": "胜率", "value": _fmt_pct(m.win_rate), "tone": ""},
            {"label": "盈亏比", "value": _fmt_num(m.profit_factor), "tone": ""},
            {"label": "换手率", "value": _fmt_num(m.turnover), "tone": ""},
        ]

        return render_html_report(
            {
                "title": bt.name or f"回测报告 #{bt.id}",
                "date_from": str(bt.date_from),
                "date_to": str(bt.date_to),
                "init_capital": f"{float(bt.init_capital):,.0f}",
                "benchmark": bt.benchmark,
                "strategy_name": bt.strategy_name,
                "strategy_version": bt.strategy_version,
                "metric_cards": metric_cards,
                "analysis": a.model_dump(by_alias=True),
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
        )

    async def compare(self, user_id: int, payload: CompareBacktestsRequest) -> CompareReportView:
        rows: list[CompareRowView] = []
        for bt_id in payload.backtest_ids:
            bt_view = await self._bt_service.get_backtest(user_id, bt_id)
            if bt_view.status != "succeeded":
                raise ValidationFailedError(f"回测 #{bt_id} 尚未完成，无法对比")
            metrics = await self._bt_service.get_metrics(user_id, bt_id)
            raw = await self._load_raw_series(bt_id)
            bm = build_report_analysis(raw["equity"], raw["trades"], raw["positions"])[
                "benchmark_metrics"
            ]
            rows.append(
                CompareRowView(
                    backtest_id=bt_id,
                    name=bt_view.name,
                    strategy_name=bt_view.strategy_name,
                    strategy_version=bt_view.strategy_version,
                    date_from=bt_view.date_from,
                    date_to=bt_view.date_to,
                    metrics=metrics,
                    benchmark_metrics=BenchmarkMetricsView.model_validate(bm),
                )
            )
        return CompareReportView(rows=rows)

    async def _require_succeeded(self, user_id: int, backtest_id: int) -> None:
        bt = await self._bt_service.get_backtest(user_id, backtest_id)
        if bt.status != "succeeded":
            raise ValidationFailedError("仅已完成的回测可查看分析报告")

    async def _load_raw_series(self, backtest_id: int) -> dict[str, list[dict[str, Any]]]:
        equity_rows = await self._bt_repo.list_equity(backtest_id)
        if not equity_rows:
            raise NotFoundError("回测结果尚未生成")
        trade_rows = await self._bt_repo.list_all_trades(backtest_id)
        pos_rows = await self._bt_repo.list_positions(backtest_id)
        equity = [
            {
                "trade_date": r.trade_date,
                "nav": float(r.nav) if r.nav is not None else 0.0,
                "benchmark_nav": float(r.benchmark_nav) if r.benchmark_nav is not None else None,
                "drawdown": float(r.drawdown) if r.drawdown is not None else None,
            }
            for r in equity_rows
        ]
        trades = [
            {
                "trade_date": t.trade_date,
                "code": t.code,
                "side": t.side,
                "pnl": float(t.pnl) if t.pnl is not None else None,
            }
            for t in trade_rows
        ]
        positions = [
            {
                "trade_date": p.trade_date,
                "code": p.code,
                "weight": float(p.weight) if p.weight is not None else None,
            }
            for p in pos_rows
        ]
        return {"equity": equity, "trades": trades, "positions": positions}


def _fmt_pct(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return "—"
