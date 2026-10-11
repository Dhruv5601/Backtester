from io import BytesIO
from datetime import datetime
import math
import numbers

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    LongTable,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)


# Matplotlib's default color cycle is used consistently across report charts.
STRATEGY_COLOR = "C0"
BENCHMARK_COLOR = "C1"
ENTRY_COLOR = "C2"
EXIT_COLOR = "C3"
STRATEGY_HEX = "#1F77B4"
BENCHMARK_HEX = "#FF7F0E"

NAVY = colors.HexColor("#16324F")
LIGHT_BLUE = colors.HexColor("#EAF0F6")
MID_GREY = colors.HexColor("#526579")
BORDER = colors.HexColor("#CFD8E3")
TEXT_COLOR = colors.HexColor("#243447")
PALE_BLUE = colors.HexColor("#F5F8FB")
PAGE_WIDTH, PAGE_HEIGHT = A4


def _to_number(value):
    """Convert report values such as '12.34%' to a float when possible."""
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return math.nan


def _safe_stat(value):
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, numbers.Real):
        if not math.isfinite(float(value)):
            return "N/A" if math.isnan(float(value)) else "∞"
        return f"{value:.2f}"
    return str(value)


def _make_chart_image(fig, width, height):
    """Save a Matplotlib figure to a ReportLab image without writing temp files."""
    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(
        buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=width, height=height)


def _style_table(table, header=True, first_column_shaded=False, compact=False):
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8 if compact else 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6 if compact else 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6 if compact else 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4 if compact else 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 if compact else 6),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    if first_column_shaded:
        commands.append(("BACKGROUND", (0, 1), (0, -1), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


def _make_metric_card(label, value, accent, styles, height=18 * mm):
    card_text_style = ParagraphStyle(
        f"Card_{label.replace(' ', '_')}",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=19,
        textColor=MID_GREY,
        alignment=TA_LEFT,
    )
    value = str(value)
    return Paragraph(
        f'<font color="{accent}"><b>{label.upper()}</b></font>'
        f'<br/><font size="15" color="{accent}"><b>{value}</b></font>',
        card_text_style,
    )


def _make_card_grid(rows, widths, row_heights=None):
    table = Table(rows, colWidths=widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.65, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 10 * mm, PAGE_WIDTH - doc.rightMargin, 10 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MID_GREY)
    canvas.drawString(doc.leftMargin, 6 * mm, "QUANT BACKTEST REPORT")
    canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 6 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf_report(
    output_path,
    asset,
    start_date,
    end_date,
    initial_capital,
    performance_report,
    trade_stats_df,
    trades_df,
    df,
):
    """Create a multi-page backtest PDF with a consistent Matplotlib theme."""
    if df is None or df.empty:
        raise ValueError("Cannot create a PDF report without backtest data.")

    required_columns = {"Equity", "Benchmark_Equity", "Close"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Backtest data is missing required columns: {sorted(missing)}")

    trades_df = trades_df.copy() if trades_df is not None else pd.DataFrame()
    trade_stats_df = (
        trade_stats_df.copy() if trade_stats_df is not None else pd.DataFrame()
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=13 * mm,
        bottomMargin=16 * mm,
        title=f"{asset} Quant Backtest Report",
        author="Quant Backtester",
    )
    content_width = PAGE_WIDTH - doc.leftMargin - doc.rightMargin
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=NAVY,
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
        textColor=MID_GREY,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=NAVY,
        spaceBefore=4,
        spaceAfter=5,
        keepWithNext=True,
    )
    small_heading_style = ParagraphStyle(
        "SmallHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=NAVY,
        spaceBefore=3,
        spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=8.3,
        leading=11.2,
        textColor=TEXT_COLOR,
        alignment=TA_LEFT,
        spaceAfter=3,
    )
    note_style = ParagraphStyle(
        "ReportNote",
        parent=body_style,
        fontSize=7.5,
        leading=10,
        textColor=MID_GREY,
        spaceAfter=0,
    )

    def pval(metric, column):
        try:
            return str(performance_report.loc[metric, column])
        except (KeyError, TypeError, AttributeError):
            return "N/A"

    strategy_final = float(df["Equity"].iloc[-1])
    benchmark_final = float(df["Benchmark_Equity"].iloc[-1])
    strategy_return_text = pval("Total Return", "Strategy")
    benchmark_return_text = pval("Total Return", "Benchmark")
    strategy_return = _to_number(strategy_return_text)
    benchmark_return = _to_number(benchmark_return_text)
    return_gap = strategy_return - benchmark_return
    strategy_cagr = pval("CAGR", "Strategy")
    strategy_volatility = pval("Volatility", "Strategy")
    benchmark_volatility = pval("Volatility", "Benchmark")
    strategy_drawdown = pval("Max drawdown", "Strategy")
    benchmark_drawdown = pval("Max drawdown", "Benchmark")
    strategy_sharpe = pval("Sharpe Ratio", "Strategy")
    benchmark_sharpe = pval("Sharpe Ratio", "Benchmark")
    completed_count = len(trades_df)
    story = []

    # ------------------------------------------------------------------
    # PAGE 1 — Executive summary
    # ------------------------------------------------------------------
    story.append(Paragraph("QUANT BACKTEST REPORT", title_style))
    story.append(Paragraph(f"{asset}  ·  {start_date} to {end_date}", subtitle_style))

    cards = _make_card_grid(
        [
            [
                _make_metric_card("Strategy Return", strategy_return_text, STRATEGY_HEX, styles),
                _make_metric_card("Benchmark Return", benchmark_return_text, BENCHMARK_HEX, styles),
            ],
            [
                _make_metric_card("Strategy CAGR", strategy_cagr, STRATEGY_HEX, styles),
                _make_metric_card("Completed Trades", str(completed_count), "#16324F", styles),
            ],
        ],
        widths=[content_width / 2, content_width / 2],
        row_heights=[19 * mm, 19 * mm],
    )
    story.append(cards)
    story.append(Spacer(1, 5 * mm))

    # Equity curve — preserve the colors used by the visualization module.
    fig, ax = plt.subplots(figsize=(10, 5.45))
    ax.plot(df.index, df["Equity"], label="Strategy", color=STRATEGY_COLOR, linewidth=1.8)
    ax.plot(
        df.index,
        df["Benchmark_Equity"],
        label="Benchmark",
        color=BENCHMARK_COLOR,
        linewidth=1.8,
    )
    ax.set_title("Strategy vs Benchmark Equity", fontsize=12, color="#16324F", pad=10)
    ax.set_ylabel("Portfolio Value ($)", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value:,.0f}"))
    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.tick_params(axis="both", labelsize=7.5)
    ax.legend(frameon=False, loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.22, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    story.append(_make_chart_image(fig, content_width, 112 * mm))
    story.append(Spacer(1, 3 * mm))

    comparison = (
        "outperformed" if strategy_return > benchmark_return
        else "underperformed" if strategy_return < benchmark_return
        else "matched"
    )
    gap_phrase = (
        f"a {abs(return_gap):.2f}-percentage-point higher return"
        if return_gap > 0
        else f"a {abs(return_gap):.2f}-percentage-point lower return"
        if return_gap < 0
        else "the same total return"
    )
    overview_text = (
        f"Across this test period, the strategy <b>{comparison}</b> the benchmark, "
        f"returning {strategy_return_text} compared with {benchmark_return_text} — "
        f"{gap_phrase}. Annualized volatility was {strategy_volatility} for the strategy "
        f"and {benchmark_volatility} for the benchmark. Maximum drawdown was "
        f"{strategy_drawdown} and {benchmark_drawdown}, respectively. These results "
        f"are historical and do not imply future performance."
    )
    overview_panel = Table(
        [[
            Paragraph("PERFORMANCE OVERVIEW", ParagraphStyle(
                "OverviewPanelTitle", parent=styles["Normal"],
                fontName="Helvetica-Bold", fontSize=8, textColor=NAVY,
                leading=10, spaceAfter=3,
            )),
            Paragraph(overview_text, note_style),
        ]],
        colWidths=[37 * mm, content_width - 37 * mm],
    )
    overview_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(overview_panel)
    story.append(Spacer(1, 3 * mm))

    final_value_data = [[
        Paragraph(f"<b>INITIAL CAPITAL</b><br/>${initial_capital:,.2f}", note_style),
        Paragraph(f"<b>FINAL STRATEGY EQUITY</b><br/>${strategy_final:,.2f}", note_style),
        Paragraph(f"<b>FINAL BENCHMARK EQUITY</b><br/>${benchmark_final:,.2f}", note_style),
    ]]
    final_value_table = Table(final_value_data, colWidths=[content_width / 3] * 3)
    final_value_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(final_value_table)
    story.append(Spacer(1, 3 * mm))

    net_profit_gap = strategy_final - benchmark_final
    quick_comparison = Table(
        [[
            Paragraph(f'<b>STRATEGY NET PROFIT</b><br/><font color="#1F77B4">${strategy_final - initial_capital:,.2f}</font>', note_style),
            Paragraph(f'<b>BENCHMARK NET PROFIT</b><br/><font color="#FF7F0E">${benchmark_final - initial_capital:,.2f}</font>', note_style),
            Paragraph(f'<b>ENDING EQUITY GAP</b><br/><font color="#16324F">${net_profit_gap:+,.2f}</font>', note_style),
        ]],
        colWidths=[content_width / 3] * 3,
    )
    quick_comparison.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(quick_comparison)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Test setup: 20/50-day moving-average crossover · long-only · next-session open execution · 0.05% transaction cost per side.",
        note_style,
    ))
    story.append(Spacer(1, 2 * mm))
    guide_table = Table([[
        Paragraph("<b>REPORT GUIDE</b>", note_style),
        Paragraph(
            "Page 2 · Risk-adjusted performance and drawdown  &nbsp; |  &nbsp; "
            "Page 3 · Trade statistics and execution chart  &nbsp; |  &nbsp; "
            "Page 4+ · Full ledger, methodology, and any open position",
            note_style,
        ),
    ]], colWidths=[27 * mm, content_width - 27 * mm])
    guide_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(guide_table)
    story.append(PageBreak())

    # ------------------------------------------------------------------
    # PAGE 2 — Performance and risk
    # ------------------------------------------------------------------
    story.append(Paragraph("PERFORMANCE &amp; RISK ANALYSIS", title_style))
    story.append(Paragraph(f"{asset}  ·  {start_date} to {end_date}", subtitle_style))

    risk_cards = _make_card_grid(
        [
            [
                _make_metric_card("Strategy Max Drawdown", strategy_drawdown, STRATEGY_HEX, styles),
                _make_metric_card("Benchmark Max Drawdown", benchmark_drawdown, BENCHMARK_HEX, styles),
            ],
            [
                _make_metric_card("Strategy Sharpe Ratio", strategy_sharpe, STRATEGY_HEX, styles),
                _make_metric_card("Benchmark Sharpe Ratio", benchmark_sharpe, BENCHMARK_HEX, styles),
            ],
        ],
        widths=[content_width / 2, content_width / 2],
        row_heights=[17 * mm, 17 * mm],
    )
    story.append(risk_cards)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Performance Comparison", heading_style))

    performance_data = [["METRIC", "STRATEGY", "BENCHMARK"]]
    for metric, row in performance_report.iterrows():
        performance_data.append([str(metric), str(row.get("Strategy", "N/A")), str(row.get("Benchmark", "N/A"))])
    performance_table = Table(
        performance_data,
        colWidths=[content_width * 0.40, content_width * 0.30, content_width * 0.30],
        repeatRows=1,
    )
    _style_table(performance_table)
    performance_table.setStyle(TableStyle([
        ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor("#1F77B4")),
        ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor("#FF7F0E")),
    ]))
    story.append(performance_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Drawdown Through Time", heading_style))

    strategy_dd = (df["Equity"] / df["Equity"].cummax() - 1) * 100
    benchmark_dd = (df["Benchmark_Equity"] / df["Benchmark_Equity"].cummax() - 1) * 100
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(df.index, strategy_dd, label="Strategy", color=STRATEGY_COLOR, linewidth=1.5)
    ax.fill_between(df.index, strategy_dd, 0, color=STRATEGY_COLOR, alpha=0.10)
    ax.plot(df.index, benchmark_dd, label="Benchmark", color=BENCHMARK_COLOR, linewidth=1.5)
    ax.fill_between(df.index, benchmark_dd, 0, color=BENCHMARK_COLOR, alpha=0.07)
    ax.axhline(0, color="#7A8793", linewidth=0.7)
    ax.set_ylabel("Drawdown (%)", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.set_title("Strategy vs Benchmark Drawdown", fontsize=11, color="#16324F", pad=8)
    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.tick_params(axis="both", labelsize=7.5)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(True, alpha=0.22, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    story.append(_make_chart_image(fig, content_width, 84 * mm))
    story.append(Spacer(1, 3 * mm))

    strat_vol = _to_number(strategy_volatility)
    bench_vol = _to_number(benchmark_volatility)
    strat_dd_num = _to_number(strategy_drawdown)
    bench_dd_num = _to_number(benchmark_drawdown)
    if math.isfinite(strat_vol) and math.isfinite(bench_vol):
        vol_note = (
            f"Strategy annualized volatility was lower ({strategy_volatility} vs {benchmark_volatility})."
            if abs(strat_vol) < abs(bench_vol)
            else f"Strategy annualized volatility was not lower ({strategy_volatility} vs {benchmark_volatility})."
        )
    else:
        vol_note = f"Annualized volatility was {strategy_volatility} for the strategy and {benchmark_volatility} for the benchmark."

    if math.isfinite(strat_dd_num) and math.isfinite(bench_dd_num):
        dd_note = (
            "The strategy's maximum drawdown was less severe than the benchmark's."
            if abs(strat_dd_num) < abs(bench_dd_num)
            else "The strategy's maximum drawdown was at least as severe as the benchmark's."
        )
    else:
        dd_note = f"Maximum drawdown was {strategy_drawdown} for the strategy and {benchmark_drawdown} for the benchmark."

    story.append(Paragraph(
        f"<b>Risk interpretation.</b> {vol_note} {dd_note} "
        "Drawdown measures declines from prior equity peaks; volatility measures variation in daily returns. "
        "Neither metric alone captures every form of investment risk.",
        body_style,
    ))

    # Dates and durations of the worst observed peak-to-trough declines.
    def worst_drawdown_period(equity):
        drawdown = equity / equity.cummax() - 1.0
        trough_date = drawdown.idxmin()
        peak_date = equity.loc[:trough_date].idxmax()
        return peak_date, trough_date, float(drawdown.loc[trough_date] * 100)

    strat_peak, strat_trough, strat_worst = worst_drawdown_period(df["Equity"])
    bench_peak, bench_trough, bench_worst = worst_drawdown_period(df["Benchmark_Equity"])
    dd_period_table = Table([
        [
            Paragraph(
                f'<font color="#1F77B4"><b>STRATEGY WORST DRAWDOWN</b></font><br/>'
                f'{strat_worst:.2f}% · Peak {strat_peak:%Y-%m-%d} → Trough {strat_trough:%Y-%m-%d}',
                note_style,
            ),
            Paragraph(
                f'<font color="#FF7F0E"><b>BENCHMARK WORST DRAWDOWN</b></font><br/>'
                f'{bench_worst:.2f}% · Peak {bench_peak:%Y-%m-%d} → Trough {bench_trough:%Y-%m-%d}',
                note_style,
            ),
        ]
    ], colWidths=[content_width / 2, content_width / 2])
    dd_period_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 2 * mm))
    story.append(dd_period_table)
    story.append(PageBreak())

    # ------------------------------------------------------------------
    # PAGE 3 — Trade analysis and the existing price/entry/exit visual
    # ------------------------------------------------------------------
    story.append(Paragraph("TRADE ANALYSIS", title_style))
    story.append(Paragraph("Statistics calculated from completed strategy trades", subtitle_style))

    def stat_value(metric, default="N/A"):
        try:
            return _safe_stat(trade_stats_df.loc[metric, "Statistics"])
        except (KeyError, TypeError, AttributeError):
            return default

    trade_highlights = _make_card_grid(
        [[
            _make_metric_card("Win Rate", stat_value("Win Rate"), STRATEGY_HEX, styles),
            _make_metric_card("Profit Factor", stat_value("Profit Factor"), STRATEGY_HEX, styles),
            _make_metric_card("Expectancy", stat_value("Expectancy"), STRATEGY_HEX, styles),
            _make_metric_card("Average Duration", stat_value("Average Trade Duration"), "#16324F", styles),
        ]],
        widths=[content_width / 4] * 4,
        row_heights=[17 * mm],
    )
    story.append(trade_highlights)
    story.append(Spacer(1, 3 * mm))

    integer_stat_names = {
        "Total Trades", "Winning Trades", "Losing Trades", "Break Even Trades",
        "Longest Winning Streak", "Longest Losing Streak",
    }

    def format_trade_stat(metric, value):
        if value is None or pd.isna(value):
            return "N/A"
        if metric in integer_stat_names and isinstance(value, numbers.Real):
            return str(int(value))
        return _safe_stat(value)

    stat_items = []
    if not trade_stats_df.empty:
        for metric, row in trade_stats_df.iterrows():
            label = str(metric)
            stat_items.append((label, format_trade_stat(label, row.get("Statistics", "N/A"))))

    stat_pairs = []
    for i in range(0, len(stat_items), 2):
        left = stat_items[i]
        right = stat_items[i + 1] if i + 1 < len(stat_items) else ("", "")
        stat_pairs.append([left[0], left[1], right[0], right[1]])

    stats_data = [["STATISTIC", "VALUE", "STATISTIC", "VALUE"]] + stat_pairs
    stats_table = Table(
        stats_data,
        colWidths=[content_width * 0.29, content_width * 0.21, content_width * 0.29, content_width * 0.21],
        repeatRows=1,
    )
    _style_table(stats_table, compact=True)
    story.append(stats_table)
    story.append(Spacer(1, 4 * mm))

    if not trades_df.empty and {"Entry_date", "Exit_date", "Entry_price", "Exit_price"}.issubset(trades_df.columns):
        plot_trades = trades_df.copy()
        plot_trades["Entry_date"] = pd.to_datetime(plot_trades["Entry_date"])
        plot_trades["Exit_date"] = pd.to_datetime(plot_trades["Exit_date"])
        plot_trades = plot_trades[
            (plot_trades["Entry_date"] >= pd.Timestamp(df.index.min()))
            & (plot_trades["Exit_date"] <= pd.Timestamp(df.index.max()))
        ]
    else:
        plot_trades = pd.DataFrame()

    story.append(Paragraph("Price and Trade Execution", heading_style))
    fig, ax = plt.subplots(figsize=(10, 4.65))
    ax.plot(df.index, df["Close"], color=STRATEGY_COLOR, linewidth=1.25, label=f"{asset} Close")
    if not plot_trades.empty:
        ax.scatter(
            plot_trades["Entry_date"], plot_trades["Entry_price"],
            marker="^", color=ENTRY_COLOR, edgecolors="white", linewidths=0.35,
            s=42, zorder=5, label="Entry",
        )
        ax.scatter(
            plot_trades["Exit_date"], plot_trades["Exit_price"],
            marker="v", color=EXIT_COLOR, edgecolors="white", linewidths=0.35,
            s=42, zorder=5, label="Exit",
        )
    ax.set_title(f"{asset} Price with Strategy Trades", fontsize=11, color="#16324F", pad=8)
    ax.set_ylabel("Price ($)", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.tick_params(axis="both", labelsize=7.5)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    ax.grid(True, alpha=0.22, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    story.append(_make_chart_image(fig, content_width, 91 * mm))
    story.append(Spacer(1, 3 * mm))

    # Best and worst completed trade, derived directly from trades_df.
    if not trades_df.empty and "Net_return" in trades_df.columns:
        best = trades_df.loc[trades_df["Net_return"].idxmax()]
        worst = trades_df.loc[trades_df["Net_return"].idxmin()]
        best_ret = float(best["Net_return"]) * 100
        worst_ret = float(worst["Net_return"]) * 100
        best_range = f"{pd.to_datetime(best['Entry_date']).strftime('%Y-%m-%d')} to {pd.to_datetime(best['Exit_date']).strftime('%Y-%m-%d')}"
        worst_range = f"{pd.to_datetime(worst['Entry_date']).strftime('%Y-%m-%d')} to {pd.to_datetime(worst['Exit_date']).strftime('%Y-%m-%d')}"
        best_worst_style = ParagraphStyle(
            "BestWorstTrade", parent=note_style, leading=16, fontSize=7.5,
        )
        bw_data = [[
            Paragraph(
                f'<font color="#2E8B57"><b>BEST TRADE</b></font><br/>'
                f'<font size="13"><b>{best_ret:+.2f}%</b></font><br/>'
                f'<font size="7.5">{best_range}</font>', best_worst_style,
            ),
            Paragraph(
                f'<font color="#C0392B"><b>WORST TRADE</b></font><br/>'
                f'<font size="13"><b>{worst_ret:+.2f}%</b></font><br/>'
                f'<font size="7.5">{worst_range}</font>', best_worst_style,
            ),
        ]]
        bw_table = Table(bw_data, colWidths=[content_width / 2, content_width / 2])
        bw_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(bw_table)
    else:
        story.append(Paragraph("No completed trades are available for best/worst trade analysis.", body_style))

    story.append(Spacer(1, 2 * mm))
    win_rate_num = _to_number(stat_value("Win Rate"))
    avg_win_num = _to_number(stat_value("Average Win"))
    avg_loss_num = _to_number(stat_value("Average Loss"))
    expectancy_num = _to_number(stat_value("Expectancy"))
    profit_factor_num = _to_number(stat_value("Profit Factor"))
    if completed_count and all(math.isfinite(v) for v in [win_rate_num, avg_win_num, avg_loss_num, expectancy_num]):
        trade_interpretation = (
            f"Across {completed_count} completed trades, the win rate was {win_rate_num:.2f}%. "
            f"Average winning and losing trades were {avg_win_num:.2f}% and {avg_loss_num:.2f}%, "
            f"respectively; expectancy was {expectancy_num:.2f}% per trade. "
        )
        if math.isfinite(profit_factor_num):
            trade_interpretation += f"The profit factor was {profit_factor_num:.2f}. "
        trade_interpretation += "These are historical sample statistics; a small trade count can make them unstable."
    else:
        trade_interpretation = "No completed trades are available to estimate win rate, expectancy, or profit factor."
    trade_interpretation_panel = Table(
        [[
            Paragraph("TRADE PROFILE", ParagraphStyle(
                "TradeProfileTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
                fontSize=8, leading=10, textColor=NAVY,
            )),
            Paragraph(trade_interpretation, note_style),
        ]],
        colWidths=[30 * mm, content_width - 30 * mm],
    )
    trade_interpretation_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(trade_interpretation_panel)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Trade statistics are calculated from completed trades only. An open position, if any, is shown separately in the final section and is not counted as a completed trade.",
        note_style,
    ))
    story.append(PageBreak())

    # ------------------------------------------------------------------
    # PAGE 4+ — Full trade ledger and methodology
    # ------------------------------------------------------------------
    story.append(Paragraph("COMPLETED TRADE LEDGER", title_style))
    story.append(Paragraph(f"{asset}  ·  {start_date} to {end_date}", subtitle_style))

    if trades_df.empty:
        story.append(Paragraph("No completed trades were recorded during this backtest period.", body_style))
    else:
        ledger_data = [[
            "ENTRY DATE", "ENTRY PRICE", "EXIT DATE", "EXIT PRICE",
            "GROSS RETURN", "NET RETURN", "DAYS",
        ]]
        for _, trade in trades_df.iterrows():
            entry_date = pd.to_datetime(trade.get("Entry_date"))
            exit_date = pd.to_datetime(trade.get("Exit_date"))
            days = max(0, (exit_date - entry_date).days) if pd.notna(entry_date) and pd.notna(exit_date) else "N/A"
            gross = trade.get("Gross_return", math.nan)
            net = trade.get("Net_return", math.nan)
            gross_text = f"{float(gross) * 100:.2f}%" if pd.notna(gross) else "N/A"
            net_text = f"{float(net) * 100:.2f}%" if pd.notna(net) else "N/A"
            ledger_data.append([
                entry_date.strftime("%Y-%m-%d") if pd.notna(entry_date) else "N/A",
                f"{float(trade.get('Entry_price')):,.2f}" if pd.notna(trade.get("Entry_price")) else "N/A",
                exit_date.strftime("%Y-%m-%d") if pd.notna(exit_date) else "N/A",
                f"{float(trade.get('Exit_price')):,.2f}" if pd.notna(trade.get("Exit_price")) else "N/A",
                gross_text,
                net_text,
                str(days),
            ])

        ledger_table = LongTable(
            ledger_data,
            colWidths=[27 * mm, 25 * mm, 27 * mm, 25 * mm, 23 * mm, 23 * mm, 24 * mm],
            repeatRows=1,
            hAlign="LEFT",
        )
        _style_table(ledger_table, compact=True)
        ledger_table.setStyle(TableStyle([
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (2, 0), (2, -1), "LEFT"),
            ("TEXTCOLOR", (4, 1), (4, -1), colors.HexColor("#1F77B4")),
            ("TEXTCOLOR", (5, 1), (5, -1), colors.HexColor("#FF7F0E")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.8),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(ledger_table)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Backtest Methodology", heading_style))
    methodology = (
        "<b>Signal logic:</b> A 20-day moving average crossing above the 50-day moving average "
        "generates a buy signal; a cross below generates a sell signal. The implementation is long-only. "
        "<b>Execution:</b> Signals are generated using available daily data and trades are executed at "
        "the next trading day's open. <b>Trading costs:</b> The backtester applies a 0.05% transaction "
        "cost on each side of a completed trade. <b>Benchmark:</b> Buy-and-hold equity is compounded "
        "from the asset's daily close-to-close returns. <b>Reporting:</b> Daily portfolio metrics use "
        "the equity curve; trade-level statistics use completed trades. Sharpe and Sortino calculations "
        "use zero risk-free rate / minimum acceptable return defaults in the current implementation."
    )
    methodology_panel = Table(
        [[Paragraph(methodology, body_style)]],
        colWidths=[content_width],
    )
    methodology_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(methodology_panel)

    open_position = df.attrs.get("open_position") if hasattr(df, "attrs") else None
    if open_position:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("Open Position at Period End", heading_style))
        unrealized = open_position.get("Unrealized_return")
        unrealized_text = f"{float(unrealized):+.2f}%" if unrealized is not None else "N/A"
        open_data = [
            ["Entry Date", str(open_position.get("Entry_date", "N/A")), "Entry Price", f"${float(open_position.get('Entry_price', 0)):,.2f}"],
            ["As-of Date", str(open_position.get("Current_date", "N/A")), "Current Price", f"${float(open_position.get('Current_price', 0)):,.2f}"],
            ["Unrealized Price Return", unrealized_text, "Status", str(open_position.get("Status", "Open"))],
        ]
        open_table = Table(open_data, colWidths=[38 * mm, 49 * mm, 38 * mm, 49 * mm])
        open_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT_BLUE),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(open_table)
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "The displayed unrealized return is based on entry and current prices; it is not a completed trade and may not include estimated exit costs.",
            note_style,
        ))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Research note: Backtest results are sensitive to the sample period, data quality, execution assumptions, and transaction costs. Past performance does not guarantee future results.",
        note_style,
    ))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
