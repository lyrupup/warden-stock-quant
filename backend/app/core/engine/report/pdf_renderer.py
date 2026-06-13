"""PDF 报告渲染（轻量 fpdf2，ASCII 标签避免字体依赖）。"""

from __future__ import annotations

from typing import Any


def _safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def render_pdf_report(context: dict[str, Any]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, _safe(str(context.get("title", "Backtest Report"))), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(
        0,
        8,
        _safe(f"Range: {context.get('date_from')} ~ {context.get('date_to')}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        8,
        _safe(
            f"Strategy: {context.get('strategy_name')} v{context.get('strategy_version')}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 8, "Key Metrics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for card in context.get("metric_cards") or []:
        pdf.cell(
            0,
            7,
            _safe(f"{card.get('label')}: {card.get('value')}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, _safe(f"Generated: {context.get('generated_at', '')}"))
    return bytes(pdf.output())
