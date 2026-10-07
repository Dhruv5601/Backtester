import pandas as pd
from src import strategy
from src import backtester
from src import performance
from src import visualization
from src import data

def run_backtest(period='10y', initial_capital=100000, trade_start_date=None, trade_end_date=None):

    df = data.download_data(period=period)
    data.validate_data(df)

    strategy.calculate_moving_averages(df)
    strategy.generate_signals(df)
    strategy.generate_positions(df)
    df, trades_df = backtester.run_backtest(df, initial_capital=initial_capital)
    performance_report = performance.calculate_performance(df, initial_capital=initial_capital)
    dict2,trade_performance = performance.calculate_trade_statistics(trades_df)
    performance_report = pd.DataFrame(performance_report)
    performance_report.set_index('Performance', inplace=True)
    trade_stats_df = pd.DataFrame(dict2)
    trade_stats_df.set_index('Benchmark', inplace=True)
    return df, trades_df, performance_report, trade_stats_df, trade_performance

if __name__ == "__main__":
    df, trades_df, performance_report, trade_stats_df, trade_performance = run_backtest(period='5y',initial_capital=50000)