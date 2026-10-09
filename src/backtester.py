import pandas as pd
import numpy as np


def run_backtest(df, initial_capital=100000):
    transaction_cost = 0.0005
    df = df.copy()

    df["Market_Return"] = df["Close"].pct_change().fillna(0.0)
    df["Strategy_Return"] = 0.0
    df["Execution"] = np.nan

    completed_trades = []

    position = 0
    entry_date = None
    entry_price = None

    strategy_returns = np.zeros(len(df), dtype=float)

    # Execute signals at the next trading day's open.
    # The final day's signal cannot execute because there is no next day.
    for i in range(len(df) - 1):
        signal = int(df["Signal"].iloc[i])

        execution_idx = i + 1
        execution_date = df.index[execution_idx]
        execution_price = df["Open"].iloc[execution_idx]

        if pd.isna(execution_price) or execution_price <= 0:
            continue

        execution_price = float(execution_price)

        # Enter a long position.
        if signal == 1 and position == 0:
            position = 1
            entry_date = execution_date
            entry_price = execution_price

            df.loc[execution_date, "Execution"] = entry_price

            # Charge entry transaction cost.
            strategy_returns[execution_idx] -= transaction_cost

        # Exit a long position.
        elif signal == -1 and position == 1:
            exit_date = execution_date
            exit_price = execution_price

            df.loc[execution_date, "Execution"] = exit_price

            gross_return = exit_price / entry_price - 1.0

            net_return = (
                (1.0 - transaction_cost)
                * (1.0 + gross_return)
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

            position = 0
            entry_date = None
            entry_price = None

            # Charge exit transaction cost.
            strategy_returns[execution_idx] -= transaction_cost

    # Calculate the daily returns from the position held during
    # each close-to-close interval, using the previous day's signal.
    held_position = 0

    for i in range(len(df)):
        if i > 0:
            previous_signal = int(df["Signal"].iloc[i - 1])

            if previous_signal == 1 and held_position == 0:
                held_position = 1
            elif previous_signal == -1 and held_position == 1:
                held_position = 0

        if held_position == 1:
            strategy_returns[i] += float(df["Market_Return"].iloc[i])

    # Apply entry and exit costs multiplicatively on execution dates.
    # This keeps the transaction-cost treatment consistent with
    # the return calculation used for completed trades.
    execution_dates = df.index[df["Execution"].notna()]

    for execution_date in execution_dates:
        strategy_returns[df.index.get_loc(execution_date)] = (
            (1.0 + strategy_returns[df.index.get_loc(execution_date)])
            * (1.0 - transaction_cost)
            - 1.0
        )

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