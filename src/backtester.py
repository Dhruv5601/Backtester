import pandas as pd
import numpy as np
df = pd.read_csv(r'C:\Users\dodhr\Desktop\R2Q Python\Backtester\data\SPY.csv', index_col=0, parse_dates=True)

def run_backtest(df, initial_capital=100000):

    transaction_cost = 0.0005
    filt = (df['Signal'] == 1) | (df['Signal'] == -1)

    exit_prices = np.array([])
    entry_prices = np.array([])

    df['Strategy_Return'] = 0.0
    df['Market_Return'] = ((df['Close'] - df['Close'].shift(1))/df['Close'].shift(1))

    df.loc[df['Position'] == 1, 'Strategy_Return'] = df.loc[df['Position'] == 1, 'Market_Return']

    entry_day = (df['Position'] == 1) & (df['Position'].shift(1) == 0)
    exit_day = ((df['Position'] == 0)) & (df['Position'].shift(1) == 1)

    df.loc[filt.shift(1, fill_value = False), 'Execution'] = df['Open']

    
    for index, signal in df['Signal'].items():
        i = df.index.get_loc(index)

        if signal == 1 and df.loc[index, 'Position'] == 0:
            if i == len(df) - 1:
                continue
            entry_prices = np.append(entry_prices,df.iloc[i + 1]['Execution'])

        elif signal == -1 and df.loc[index, 'Position'] == 1:
            if i == len(df) - 1:
                continue
            exit_prices = np.append(exit_prices,df.iloc[i + 1]['Execution'])

    df.loc[entry_day, 'Strategy_Return'] = (df['Close'] - df['Open']) / df['Open']
    df.loc[exit_day, 'Strategy_Return'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)

    df.loc[entry_day, 'Strategy_Return']  =  (1 - transaction_cost) * (1 +  df.loc[entry_day, 'Strategy_Return']) - 1
    df.loc[exit_day, 'Strategy_Return']  = (1 - transaction_cost) * (1 +  df.loc[exit_day, 'Strategy_Return']) - 1
    df['Equity'] = initial_capital * (1 + df['Strategy_Return']).cumprod()

    if len(entry_prices) > len(exit_prices):
        open_entry = entry_prices[-1]
        entry_prices = entry_prices[:-1]
    elif len(entry_prices) < len(exit_prices):
        raise ValueError("More exits than entries detected")
    gross_trade_returns = (exit_prices - entry_prices) / entry_prices

    net_trade_returns = ((1 - transaction_cost)* (1 + gross_trade_returns)* (1 - transaction_cost)- 1)

    trades_capital = initial_capital * (1 + net_trade_returns).cumprod()

    df['Market_Return'] = df['Market_Return'].fillna(0)
    df['Benchmark_Return'] = df['Market_Return']
    df['Benchmark_Equity'] = initial_capital * (1+ df['Benchmark_Return']).cumprod()
    
    first_entry = entry_prices[0]
    first_exit = exit_prices[0]

    return df


