from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
import math

import numpy as np
import pandas as pd

from main import run_backtest
from src.pdf_report import generate_pdf_report
from src import visualization

app = Flask(__name__)


def clean_json(value):
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]

    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())

    if value is None or isinstance(value, (str, int, bool)):
        return value

    return value


def clean_records(df):
    if df is None or df.empty:
        return []

    records = df.reset_index().to_dict(orient="records")

    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
            elif isinstance(value, (pd.Timestamp, np.datetime64)):
                record[key] = pd.Timestamp(value).strftime("%Y-%m-%d")
            elif isinstance(value, np.generic):
                record[key] = value.item()

    return records


def clean_trade_stats(trade_stats_df):
    if not isinstance(trade_stats_df, pd.DataFrame) or trade_stats_df.empty:
        return {"Benchmark": [], "Statistics": []}

    return {
        "Benchmark": trade_stats_df.index.tolist(),
        "Statistics": trade_stats_df.iloc[:, 0].tolist()
    }


def validate_request(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid request data.")

    period = data.get("period", "5y")
    initial_capital = data.get("initial_capital", 100000)
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    ticker = data.get("ticker", "SPY")

    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Please enter a valid stock ticker.")

    ticker = ticker.strip().upper()

    if period == "custom":
        if not start_date or not end_date:
            raise ValueError(
                "Start date and end date are required for a custom backtest."
            )

        if start_date >= end_date:
            raise ValueError("End date must be after the start date.")

    try:
        initial_capital = float(initial_capital)
    except (TypeError, ValueError):
        raise ValueError("Initial capital must be a positive number.")

    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("Initial capital must be a positive number.")

    return period, initial_capital, start_date, end_date, ticker


def execute_backtest(data):
    (
        period,
        initial_capital,
        start_date,
        end_date,
        ticker
    ) = validate_request(data)

    results = run_backtest(
        period=period,
        initial_capital=initial_capital,
        start_date=start_date if period == "custom" else None,
        end_date=end_date if period == "custom" else None,
        ticker=ticker
    )

    return (
        period,
        initial_capital,
        start_date,
        end_date,
        ticker,
        results
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run-backtest", methods=["POST"])
def run_backtest_route():
    try:
        (
            period,
            initial_capital,
            start_date,
            end_date,
            ticker,
            results
        ) = execute_backtest(request.get_json())

        (
            df,
            trades_df,
            performance_report,
            trade_stats_df,
            trade_performance
        ) = results

        equity_raw = visualization.get_equity_curve_data(df)
        drawdown_raw = visualization.get_drawdown_data(df)

        equity_curve_data = [
            {
                "Date": date,
                "Equity": equity,
                "Benchmark_Equity": benchmark
            }
            for date, equity, benchmark in zip(
                equity_raw["dates"],
                equity_raw["strategy_equity"],
                equity_raw["benchmark_equity"]
            )
        ]

        drawdown_data = [
            {
                "Date": date,
                "Drawdown": strategy_dd,
                "Benchmark_Drawdown": benchmark_dd
            }
            for date, strategy_dd, benchmark_dd in zip(
                drawdown_raw["dates"],
                drawdown_raw["strategy_drawdown"],
                drawdown_raw["benchmark_drawdown"]
            )
        ]

        has_trades = trades_df is not None and not trades_df.empty

        response_data = {
            "success": True,
            "ticker": ticker,
            "has_trades": has_trades,
            "message": (
                "Backtest completed successfully."
                if has_trades
                else "No completed trades during this period."
            ),
            "performance": performance_report.to_dict(orient="index"),
            "trade_stats": clean_trade_stats(trade_stats_df),
            "trade_performance": (
                clean_records(trade_performance)
                if isinstance(trade_performance, pd.DataFrame)
                else []
            ),
            "equity_curve": equity_curve_data,
            "drawdown": drawdown_data,
            "recent_trades": clean_records(trades_df.tail(10)),
            "open_position": df.attrs.get("open_position")
        }

        return jsonify(clean_json(response_data))

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception:
        app.logger.exception("Backtest failed")

        return jsonify({
            "success": False,
            "error": (
                "The backtest could not be completed. "
                "Check the selected dates and server log for details."
            )
        }), 500


@app.route("/download-report", methods=["POST"])
def download_report_route():
    try:
        data = request.get_json()

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid request data."
            }), 400

        (
            period,
            initial_capital,
            start_date,
            end_date,
            ticker,
            results
        ) = execute_backtest(data)

        (
            df,
            trades_df,
            performance_report,
            trade_stats_df,
            trade_performance
        ) = results

        start = df.index.min().date()
        end = df.index.max().date()
        pdf_buffer = BytesIO()

        generate_pdf_report(
            pdf_buffer,
            ticker,
            start,
            end,
            initial_capital,
            performance_report,
            trade_stats_df,
            trades_df,
            df
        )

        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{ticker}_backtest_report_{start}_{end}.pdf"
        )

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception:
        app.logger.exception("PDF report generation failed")

        return jsonify({
            "success": False,
            "error": (
                "The PDF report could not be generated. "
                "Check the server log for details."
            )
        }), 500


if __name__ == "__main__":
    app.run(debug=True)