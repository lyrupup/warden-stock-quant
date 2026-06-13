"""HTML 绩效报告渲染（Jinja2 模板）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


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


def render_html_report(context: dict[str, Any]) -> str:
    """渲染自包含 HTML 绩效报告。"""
    tpl = _env.get_template("report.html")
    return tpl.render(
        fmt_pct=_fmt_pct,
        fmt_num=_fmt_num,
        **context,
    )
