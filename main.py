import pandas as pd
from src import strategy
from src import backtester

df = pd.read_csv(r'C:\Users\dodhr\Desktop\R2Q Python\Backtester\data\SPY.csv', index_col=0, parse_dates=True)

if __name__ == "__main__":
    strategy.calculate_moving_averages(df)
    strategy.generate_signals(df)
    strategy.generate_positions(df)
    backtester.run_backtest(df, initial_capital=100000)

print(df)
