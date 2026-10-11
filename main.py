import pandas as pd
from datetime import date, timedelta

from src import strategy, backtester, performance, visualization, data
from src.pdf_report import generate_pdf_report


def run_backtest(
    period="10y",
    initial_capital=100000,
    start_date=None,
    end_date=None,
    ticker="SPY"
):
    ticker = ticker.strip().upper() if isinstance(ticker, str) else ""

    if not ticker:
        raise ValueError("Please enter a valid stock ticker.")

    custom_start = None
    custom_end = None

    if period == "custom":
        if not start_date or not end_date:
            raise ValueError(
                "Start date and end date are required for a custom backtest."
            )

        custom_start = date.fromisoformat(start_date)
        custom_end = date.fromisoformat(end_date)

        if custom_start >= custom_end:
            raise ValueError("End date must be after the start date.")

        if custom_end > date.today():
            raise ValueError("End date cannot be in the future.")

        warmup_start = (
            custom_start - timedelta(days=365)
        ).isoformat()

        df = data.download_data(
            start=warmup_start,
            end=custom_end.isoformat(),
            ticker=ticker
        )
    else:
        df = data.download_data(
            period=period,
            ticker=ticker
        )

    data.validate_data(df, ticker=ticker)

    if len(df) < 2:
        raise ValueError(
            "Not enough market data for this date range. "
            "Select a wider range."
        )

    strategy.calculate_moving_averages(df)
    strategy.generate_signals(df)
    strategy.generate_positions(df)

    df, trades_df = backtester.run_backtest(
        df,
        initial_capital=initial_capital
    )

    if period == "custom":
        start_timestamp = pd.Timestamp(custom_start)
        end_timestamp = pd.Timestamp(custom_end)

        df = df.loc[
            (df.index >= start_timestamp) &
            (df.index <= end_timestamp)
        ].copy()

        if len(df) < 2:
            raise ValueError(
                "Not enough market data in the selected period. "
                "Choose a wider range."
            )

        df["Strategy_Return"] = df["Strategy_Return"].fillna(0)
        df["Benchmark_Return"] = df["Benchmark_Return"].fillna(0)

        df.iloc[0, df.columns.get_loc("Benchmark_Return")] = 0

        df["Equity"] = initial_capital * (
            1 + df["Strategy_Return"]
        ).cumprod()

        df["Benchmark_Equity"] = initial_capital * (
            1 + df["Benchmark_Return"]
        ).cumprod()

        if not trades_df.empty:
            trades_df["Entry_date"] = pd.to_datetime(
                trades_df["Entry_date"]
            )
            trades_df["Exit_date"] = pd.to_datetime(
                trades_df["Exit_date"]
            )

            trades_df = trades_df.loc[
                (trades_df["Entry_date"] <= end_timestamp) &
                (trades_df["Exit_date"] >= start_timestamp) &
                (trades_df["Exit_date"] <= end_timestamp)
            ].copy()

    performance_report = performance.calculate_performance(
        df,
        initial_capital=initial_capital
    )

    dict2, trade_performance = performance.calculate_trade_statistics(
        trades_df
    )

    performance_report = pd.DataFrame(performance_report)
    performance_report.set_index("Performance", inplace=True)

    trade_stats_df = pd.DataFrame(dict2)
    trade_stats_df.set_index("Benchmark", inplace=True)

    return (
        df,
        trades_df,
        performance_report,
        trade_stats_df,
        trade_performance
    )

if __name__ == "__main__":
    results = run_backtest(
        period="10y",
        initial_capital=100000,
        ticker="AAPL"
    )

    (
        df,
        trades_df,
        performance_report,
        trade_stats_df,
        trade_performance
    ) = results

    generate_pdf_report(
        "backtest_report.pdf",
        "AAPL",
        df.index.min().date(),
        df.index.max().date(),
        100000,
        performance_report,
        trade_stats_df,
        trades_df,
        df
    )