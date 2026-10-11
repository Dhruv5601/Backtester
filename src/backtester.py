import pandas as pd
import numpy as np


def run_backtest(df, initial_capital=100000):
    transaction_cost = 0.0005
    df = df.copy()

    if df.empty:
        raise ValueError("No market data available for backtesting.")

    required_columns = {"Open", "Close", "Signal"}
    missing = required_columns.difference(df.columns)

    if missing:
        raise ValueError(
            f"Market data is missing required columns: {sorted(missing)}"
        )

    if initial_capital <= 0:
        raise ValueError("Initial capital must be greater than zero.")

    df["Market_Return"] = df["Close"].pct_change().fillna(0.0)
    df["Strategy_Return"] = 0.0
    df["Execution"] = np.nan

    completed_trades = []

    position = 0
    entry_date = None
    entry_price = None

    strategy_returns = np.zeros(len(df), dtype=float)

    # Signals generated at a close execute at the following day's open.
    # Returns reflect only the price movements during which the strategy
    # actually holds the position.

    for i in range(1, len(df)):
        previous_signal = int(df["Signal"].iloc[i - 1])

        previous_close = float(df["Close"].iloc[i - 1])
        current_open = df["Open"].iloc[i]
        current_close = float(df["Close"].iloc[i])

        if not np.isfinite(current_close) or current_close <= 0:
            raise ValueError(
                f"Invalid closing price at {df.index[i]}."
            )

        # Default to holding the existing position overnight and
        # throughout the current session.
        if position == 1:
            if previous_close <= 0:
                raise ValueError(
                    f"Invalid previous closing price at {df.index[i - 1]}."
                )

            daily_factor = current_close / previous_close
        else:
            daily_factor = 1.0

        # An invalid open prevents execution at today's open.
        valid_open = (
            pd.notna(current_open)
            and np.isfinite(float(current_open))
            and float(current_open) > 0
        )

        if valid_open:
            current_open = float(current_open)

            # Enter at today's open.
            if previous_signal == 1 and position == 0:
                position = 1
                entry_date = df.index[i]
                entry_price = current_open

                df.loc[df.index[i], "Execution"] = entry_price

                # No overnight return before entry.
                # Apply entry cost once, then capture open-to-close return.
                daily_factor = (
                    (1.0 - transaction_cost)
                    * (current_close / current_open)
                )

            # Exit at today's open.
            elif previous_signal == -1 and position == 1:
                exit_date = df.index[i]
                exit_price = current_open

                df.loc[df.index[i], "Execution"] = exit_price

                gross_return = exit_price / entry_price - 1.0

                net_return = (
                    (1.0 - transaction_cost)
                    * (exit_price / entry_price)
                    * (1.0 - transaction_cost)
                    - 1.0
                )

                completed_trades.append({
                    "Entry_date": entry_date,
                    "Entry_price": entry_price,
                    "Exit_price": exit_price,
                    "Gross_return": gross_return,
                    "Net_return": net_return,
                    "Exit_date": exit_date
                })

                # Capture the overnight return up to the exit price,
                # then charge the exit cost once.
                daily_factor = (
                    (current_open / previous_close)
                    * (1.0 - transaction_cost)
                )

                position = 0
                entry_date = None
                entry_price = None

        # Convert the daily growth factor into a daily return.
        strategy_returns[i] = daily_factor - 1.0

    df["Strategy_Return"] = strategy_returns

    df["Equity"] = initial_capital * (
        1.0 + df["Strategy_Return"]
    ).cumprod()

    df["Benchmark_Return"] = df["Market_Return"]

    df["Benchmark_Equity"] = initial_capital * (
        1.0 + df["Benchmark_Return"]
    ).cumprod()

    trades_df = pd.DataFrame(
        completed_trades,
        columns=[
            "Entry_date",
            "Entry_price",
            "Exit_price",
            "Gross_return",
            "Net_return",
            "Exit_date"
        ]
    )

    trades_df.index.name = "Trade_no"

    # Preserve any position that remains open at the end of the data.
    open_position = None

    if position == 1 and entry_date is not None:
        current_price = float(df["Close"].iloc[-1])

        open_position = {
            "Status": "Open",
            "Entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
            "Entry_price": float(entry_price),
            "Current_date": pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d"),
            "Current_price": current_price,
            "Unrealized_return": (
                current_price / entry_price - 1.0
            ) * 100.0
        }

    df.attrs["open_position"] = open_position

    return df, trades_df