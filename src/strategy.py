import pandas as pd

df = pd.read_csv(r"C:\Users\dodhr\Desktop\R2Q Python\Backtester\data\SPY.csv", index_col=0, parse_dates=True)

def calculate_moving_averages(df):
    df['MA_20'] = df['Close'].rolling(window=20).mean()
    df['MA_50'] = df['Close'].rolling(window=50).mean()
    return df

def generate_signals(df):
    buy_signal = (df['MA_20'] > df['MA_50']) & (df['MA_20'].shift(1) <= df['MA_50'].shift(1))
    sell_signal = (df['MA_20'] < df['MA_50']) & (df['MA_20'].shift(1) >= df['MA_50'].shift(1))
    df['Signal'] = 0
    df.loc[buy_signal, 'Signal'] = 1
    df.loc[sell_signal, 'Signal'] = -1
    return df

def generate_positions(df):

    df['Position'] = 0
    position = 0
    
    for index, signal in df['Signal'].items():
        df.loc[index, 'Position'] = position

        if signal == 1 and position == 0:
            position = 1
        elif signal == -1 and position == 1:
            position = 0
        
    return df
