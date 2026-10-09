from flask import Flask, render_template, request, jsonify
from main import run_backtest
from src import visualization
import pandas as pd
import numpy as np
import math

app = Flask(__name__)


def clean_json(value):
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]

    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return None
        return float(value)

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
    if isinstance(trade_stats_df, pd.DataFrame):
        if trade_stats_df.empty:
            return {"Benchmark": [], "Statistics": []}

        return {
            "Benchmark": trade_stats_df.index.tolist(),
            "Statistics": trade_stats_df.iloc[:, 0].tolist()
        }

    if isinstance(trade_stats_df, dict):
        return trade_stats_df

    return {"Benchmark": [], "Statistics": []}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run-backtest", methods=["POST"])
def run_backtest_route():
    try:
        data = request.get_json()

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid request data."
            }), 400

        period = data.get("period", "5y")
        initial_capital = data.get("initial_capital", 100000)
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if period == "custom":
            if not start_date or not end_date:
                return jsonify({
                    "success": False,
                    "error": "Start date and end date are required for a custom backtest."
                }), 400

            if start_date >= end_date:
                return jsonify({
                    "success": False,
                    "error": "End date must be after the start date."
                }), 400

        if initial_capital is None:
            return jsonify({
                "success": False,
                "error": "Initial capital is required."
            }), 400

        initial_capital = float(initial_capital)

        if not np.isfinite(initial_capital) or initial_capital <= 0:
            return jsonify({
                "success": False,
                "error": "Initial capital must be a positive number."
            }), 400

        (
            df,
            trades_df,
            performance_report,
            trade_stats_df,
            trade_performance
        ) = run_backtest(
            period=period,
            initial_capital=initial_capital,
            start_date=start_date if period == "custom" else None,
            end_date=end_date if period == "custom" else None
        )

        performance_data = performance_report.to_dict(orient="index")
        trade_stats_data = clean_trade_stats(trade_stats_df)

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

        recent_trades_data = (
            clean_records(trades_df.tail(10))
            if has_trades else []
        )

        trade_performance_data = (
            clean_records(trade_performance)
            if isinstance(trade_performance, pd.DataFrame)
            and not trade_performance.empty
            else []
        )

        open_position = df.attrs.get("open_position")

        response_data = {
            "success": True,
            "has_trades": has_trades,
            "message": (
                "Backtest completed successfully."
                if has_trades
                else "No completed trades during this period."
            ),
            "performance": performance_data,
            "trade_stats": trade_stats_data,
            "trade_performance": trade_performance_data,
            "equity_curve": equity_curve_data,
            "drawdown": drawdown_data,
            "recent_trades": recent_trades_data,
            "open_position": open_position
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


if __name__ == "__main__":
    app.run(debug=True)
