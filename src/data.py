import yfinance as yf
import pandas as pd
from datetime import date, timedelta


def download_data(period="10y", start=None, end=None, ticker="SPY"):
    ticker = ticker.strip().upper() if isinstance(ticker, str) else ""

    if not ticker:
        raise ValueError("Please enter a valid stock ticker.")

    download_args = {
        "tickers": ticker,
        "interval": "1d",
        "auto_adjust": False,
        "progress": False,
        "multi_level_index": False,
    }

    if start is not None and end is not None:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        if start_date > end_date:
            raise ValueError(
                "Start date must be on or before the end date."
            )

        if end_date > date.today():
            raise ValueError("End date cannot be in the future.")

        download_args["start"] = start_date.isoformat()
        download_args["end"] = (
            end_date + timedelta(days=1)
        ).isoformat()
    else:
        download_args["period"] = period

    df = yf.download(**download_args)

    if df.empty:
        raise ValueError(
            f"No market data was returned for {ticker}. "
            "Check the ticker symbol and selected date range."
        )

    # Handle MultiIndex columns across yfinance versions.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns.name = None
    return df


def validate_data(df, ticker="SPY"):
    if df is None or df.empty:
        raise ValueError(
            f"No market data is available for {ticker}. "
            "Check the ticker and select a wider date range."
        )

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required market data columns: {missing_columns}"
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Market data must have a datetime index.")

    today = date.today()

    if df.index[-1].date() == today:
        df.drop(index=df.index[-1], inplace=True)

    if df.empty:
        raise ValueError(
            "No completed trading-day data is available for this range."
        )

    if df.isna().any().any():
        missing_rows = df[df.isna().any(axis=1)]
        first_row = missing_rows.iloc[0]
        first_date = missing_rows.index[0].strftime("%Y-%m-%d")
        missing_cols = first_row[first_row.isna()].index.tolist()

        raise ValueError(
            f"Missing values detected in {len(missing_rows)} row(s). "
            f"First occurrence: {first_date}; columns: {missing_cols}"
        )

    if df.index.has_duplicates:
        duplicate_dates = (
            df.index[df.index.duplicated(keep=False)]
            .strftime("%Y-%m-%d")
            .unique()
            .tolist()
        )
        raise ValueError(
            f"Duplicate dates detected: {duplicate_dates}"
        )

    if not df.index.is_monotonic_increasing:
        raise ValueError("Market data dates must be in ascending order.")

    if (df["High"] < df["Open"]).any():
        raise ValueError("Invalid market data: High is below Open.")

    if (df["High"] < df["Close"]).any():
        raise ValueError("Invalid market data: High is below Close.")

    if (df["Low"] > df["Open"]).any():
        raise ValueError("Invalid market data: Low is above Open.")

    if (df["Low"] > df["Close"]).any():
        raise ValueError("Invalid market data: Low is above Close.")

    price_columns = ["Open", "High", "Low", "Close"]

    if (df[price_columns] <= 0).any().any():
        raise ValueError("Invalid market data: prices must be positive.")

    if (df["Volume"] < 0).any():
        raise ValueError("Invalid market data: volume cannot be negative.")

    return True


def save_data(df, filepath):
    df.to_csv(filepath)


if __name__ == "__main__":
    df = download_data()
    validate_data(df)
    save_data(df, "data/SPY.csv")