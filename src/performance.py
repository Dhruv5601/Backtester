import pandas as pd
import numpy as np


def safe_ratio(numerator, denominator):
    if not np.isfinite(numerator) or not np.isfinite(denominator):
        return np.nan
    if denominator == 0:
        return np.nan
    return numerator / denominator


def calculate_performance(df, initial_capital=100000):
    if df is None or df.empty:
        raise ValueError("No market data available to calculate performance.")

    first_day = df.index.min()
    last_day = df.index.max()
    duration_years = (last_day - first_day).days / 365.2425

    current_equity = df.iloc[-1]["Equity"]
    benchmark_equity = df.iloc[-1]["Benchmark_Equity"]

    equity_return = ((current_equity - initial_capital) / initial_capital) * 100
    benchmark_return = ((benchmark_equity - initial_capital) / initial_capital) * 100

    if duration_years > 0 and current_equity > 0:
        cagr_equity = (((current_equity / initial_capital) ** (1 / duration_years)) - 1) * 100
    else:
        cagr_equity = np.nan

    if duration_years > 0 and benchmark_equity > 0:
        cagr_benchmark_equity = (((benchmark_equity / initial_capital) ** (1 / duration_years)) - 1) * 100
    else:
        cagr_benchmark_equity = np.nan

    strat_volatility, benchmark_volatility = volatility(df)
    strat_drawdown, bench_drawdown = max_drawdown(df)
    strat_sharpe, bench_sharpe = sharpe_ratio(df)
    strat_sortino, bench_sortino = sortino_ratio(df)

    dict1 = {
        "Strategy": [
            f"{equity_return:.2f}%",
            f"{cagr_equity:.2f}%" if np.isfinite(cagr_equity) else "N/A",
            f"{strat_volatility:.2f}%" if np.isfinite(strat_volatility) else "N/A",
            f"{strat_drawdown:.2f}%" if np.isfinite(strat_drawdown) else "N/A",
            f"{strat_sharpe:.2f}" if np.isfinite(strat_sharpe) else "N/A",
            f"{strat_sortino:.2f}" if np.isfinite(strat_sortino) else "N/A"
        ],
        "Benchmark": [
            f"{benchmark_return:.2f}%",
            f"{cagr_benchmark_equity:.2f}%" if np.isfinite(cagr_benchmark_equity) else "N/A",
            f"{benchmark_volatility:.2f}%" if np.isfinite(benchmark_volatility) else "N/A",
            f"{bench_drawdown:.2f}%" if np.isfinite(bench_drawdown) else "N/A",
            f"{bench_sharpe:.2f}" if np.isfinite(bench_sharpe) else "N/A",
            f"{bench_sortino:.2f}" if np.isfinite(bench_sortino) else "N/A"
        ],
        "Performance": [
            "Total Return",
            "CAGR",
            "Volatility",
            "Max drawdown",
            "Sharpe Ratio",
            "Sortino Ratio"
        ]
    }

    return dict1


def volatility(df):
    strat_std = df["Strategy_Return"].std()
    benchmark_std = df["Benchmark_Return"].std()

    strat_volatility = strat_std * (252 ** 0.5) * 100
    benchmark_volatility = benchmark_std * (252 ** 0.5) * 100

    return strat_volatility, benchmark_volatility


def max_drawdown(df):
    max_drawdown_strat = (
        (df["Equity"] - df["Equity"].cummax()) / df["Equity"].cummax()
    ).min() * 100

    max_drawdown_bench = (
        (df["Benchmark_Equity"] - df["Benchmark_Equity"].cummax())
        / df["Benchmark_Equity"].cummax()
    ).min() * 100

    return max_drawdown_strat, max_drawdown_bench


def sharpe_ratio(df, risk_free_rate=0.0):
    daily_risk_free = (1 + risk_free_rate) ** (1 / 252) - 1

    strat_daily_ret = df["Strategy_Return"].mean()
    bench_daily_ret = df["Benchmark_Return"].mean()

    strat_sharpe = safe_ratio(
        strat_daily_ret - daily_risk_free,
        df["Strategy_Return"].std()
    ) * (252 ** 0.5)

    bench_sharpe = safe_ratio(
        bench_daily_ret - daily_risk_free,
        df["Benchmark_Return"].std()
    ) * (252 ** 0.5)

    return strat_sharpe, bench_sharpe


def sortino_ratio(df, MAR=0.0):
    daily_MAR = (1 + MAR) ** (1 / 252) - 1

    strat_daily_ret = df["Strategy_Return"].mean()
    bench_daily_ret = df["Benchmark_Return"].mean()

    relative_down_ret = df["Strategy_Return"] - daily_MAR
    relative_down_ret2 = df["Benchmark_Return"] - daily_MAR

    relative_down_ret = relative_down_ret.clip(upper=0)
    relative_down_ret2 = relative_down_ret2.clip(upper=0)

    strat_downside_deviation = (
        (relative_down_ret ** 2).mean() ** 0.5
    ) * (252 ** 0.5)

    bench_downside_deviation = (
        (relative_down_ret2 ** 2).mean() ** 0.5
    ) * (252 ** 0.5)

    annual_strat_return = strat_daily_ret * 252
    annual_bench_return = bench_daily_ret * 252

    sortino_strat = safe_ratio(
        annual_strat_return - MAR,
        strat_downside_deviation
    )

    sortino_bench = safe_ratio(
        annual_bench_return - MAR,
        bench_downside_deviation
    )

    return sortino_strat, sortino_bench


def calculate_trade_statistics(trades_df):
    total_trades = len(trades_df)

    if total_trades == 0:
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        win_rate = 0
        loss_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = np.nan
        expectancy = 0
        avg_trade_duration = 0
        median_trade_duration = 0
        longest_winning_streak = 0
        longest_losing_streak = 0

        trade_performance = pd.DataFrame(
            columns=[
                "Entry_date",
                "Entry_price",
                "Exit_price",
                "Gross_return",
                "Net_return",
                "Exit_date"
            ]
        )
        trade_performance.index.name = "Trade_no"
        trade_performance.index = pd.MultiIndex.from_arrays(
            [[], []], names=["Type", "Trade_no"]
        )

    else:
        winning_trades = int((trades_df["Net_return"] > 0).sum())
        losing_trades = int((trades_df["Net_return"] < 0).sum())
        break_even_trades = int((trades_df["Net_return"] == 0).sum())

        win_rate = winning_trades / total_trades * 100
        loss_rate = losing_trades / total_trades * 100

        winning_returns = trades_df.loc[
            trades_df["Net_return"] > 0, "Net_return"
        ]
        losing_returns = trades_df.loc[
            trades_df["Net_return"] < 0, "Net_return"
        ]

        avg_win = winning_returns.mean() * 100 if winning_trades else 0
        avg_loss = losing_returns.mean() * 100 if losing_trades else 0

        if losing_trades == 0:
            profit_factor = np.nan if winning_trades == 0 else np.inf
        else:
            profit_factor = (
                winning_returns.sum() / abs(losing_returns.sum())
            )

        expectancy = (
            (win_rate / 100) * avg_win
            + (loss_rate / 100) * avg_loss
        )

        trade_durations = (
            pd.to_datetime(trades_df["Exit_date"])
            - pd.to_datetime(trades_df["Entry_date"])
        )

        avg_trade_duration = trade_durations.mean().total_seconds() / 86400
        median_trade_duration = trade_durations.median().total_seconds() / 86400

        longest_winning_streak = 0
        longest_losing_streak = 0
        current_winning_streak = 0
        current_losing_streak = 0

        for trade_return in trades_df["Net_return"]:
            if trade_return > 0:
                current_winning_streak += 1
                current_losing_streak = 0
            elif trade_return < 0:
                current_losing_streak += 1
                current_winning_streak = 0
            else:
                current_winning_streak = 0
                current_losing_streak = 0

            longest_winning_streak = max(
                longest_winning_streak, current_winning_streak
            )
            longest_losing_streak = max(
                longest_losing_streak, current_losing_streak
            )

        best_trade = trades_df.loc[
            trades_df["Net_return"] == trades_df["Net_return"].max()
        ].head(1).copy()

        worst_trade = trades_df.loc[
            trades_df["Net_return"] == trades_df["Net_return"].min()
        ].head(1).copy()

        best_trade["Type"] = "Best Trade"
        worst_trade["Type"] = "Worst Trade"

        trade_performance = pd.concat([best_trade, worst_trade])

        if not trade_performance.empty:
            trade_performance.set_index("Type", inplace=True)

    dict2 = {
        "Statistics": [
            total_trades,
            winning_trades,
            losing_trades,
            break_even_trades,
            f"{win_rate:.2f}%",
            f"{avg_win:.2f}%",
            f"{abs(avg_loss):.2f}%",
            profit_factor if np.isfinite(profit_factor) else None,
            f"{expectancy:.2f}%",
            f"{avg_trade_duration:.2f} days",
            f"{median_trade_duration:.2f} days",
            longest_winning_streak,
            longest_losing_streak
        ],
        "Benchmark": [
            "Total Trades",
            "Winning Trades",
            "Losing Trades",
            "Break Even Trades",
            "Win Rate",
            "Average Win",
            "Average Loss",
            "Profit Factor",
            "Expectancy",
            "Average Trade Duration",
            "Median Trade Duration",
            "Longest Winning Streak",
            "Longest Losing Streak"
        ]
    }

    return dict2, trade_performance