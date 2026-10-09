import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta


def download_data(period='10y', start=None, end=None):
    if start is not None and end is not None:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        if start_date > end_date:
            raise ValueError("Start date must be on or before the end date.")

        if end_date > date.today():
            raise ValueError("End date cannot be in the future.")

        download_end = (end_date + timedelta(days=1)).isoformat()

        df = yf.download('SPY',start=start_date.isoformat(),end=download_end,interval='1d',auto_adjust=False,progress=False)
    else:
        df = yf.download('SPY',period=period,interval='1d',auto_adjust=False,progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns.name = None
    return df


def validate_data(df):
    if df is None or df.empty:
        raise ValueError(
            "No market data was returned for the selected date range. "
            "Choose a wider range with available SPY trading data."
        )

    cols_list = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_list = [col for col in cols_list if col not in df.columns]

    if missing_list:
        raise KeyError(f"Missing required columns: {missing_list}")

    today = date.today()

    if df.index[-1].date() == today:
        df.drop(index=df.index[-1], inplace=True)

    if df.empty:
        raise ValueError(
            "No completed trading-day data is available for this range."
        )

    if df.isna().any().any():
        ndf = df[df.isna().any(axis=1)]
        na_index = ndf.index[0].strftime('%Y-%m-%d')
        na_cols = ndf.columns[ndf.iloc[0].isna()].tolist()

        raise ValueError(
            f"Missing values detected in {len(ndf)} row(s). "
            f"First occurrence: {na_index}; columns: {na_cols}"
        )

    if df.index.duplicated().any():
        dup_dates = (
            df.index[df.index.duplicated(keep=False)]
            .strftime('%Y-%m-%d')
            .unique()
            .tolist()
        )
        raise ValueError(f"Duplicate dates detected: {dup_dates}")

    invalid_high_open = df['High'] < df['Open']
    invalid_high_close = df['High'] < df['Close']
    invalid_low_open = df['Low'] > df['Open']
    invalid_low_close = df['Low'] > df['Close']

    if invalid_high_open.any():
        raise ValueError("Invalid market data: High is below Open.")

    if invalid_high_close.any():
        raise ValueError("Invalid market data: High is below Close.")

    if invalid_low_open.any():
        raise ValueError("Invalid market data: Low is above Open.")

    if invalid_low_close.any():
        raise ValueError("Invalid market data: Low is above Close.")

    price_columns = ['Open', 'High', 'Low', 'Close']

    if (df[price_columns] <= 0).any().any():
        raise ValueError("Invalid market data: prices must be positive.")

    if (df['Volume'] <= 0).any():
        raise ValueError("Invalid market data: volume must be positive.")

    return True


def save_data(df, filepath):
    df.to_csv(filepath)


if __name__ == "__main__":
    df = download_data()
    validate_data(df)
    save_data(df, "data/SPY.csv")