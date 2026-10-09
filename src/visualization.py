from matplotlib import pyplot as plt
from matplotlib import dates as mpl_dates

def plot_equity_curve(df):

    dates = df.index
    strat_equity = df['Equity']
    bench_equity = df['Benchmark_Equity']
    
    plt.figure(figsize=(12, 6))
    
    plt.plot(dates, strat_equity, linewidth = 1.5, label='Strategy Equity')
    plt.plot(dates, bench_equity, linewidth = 1.5, label='Benchmark Equity')
    
    ax = plt.gca()
    locator = mpl_dates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    date_format = mpl_dates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_formatter(date_format)
    
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    
    plt.legend()
    plt.title('Strategy vs Benchmark Equity')
    
    plt.xlim(dates.min(), dates.max())
    plt.grid(True, alpha=0.3)
    plt.show()

def plot_drawdown(df):

    max_drawdown_strat = ((df['Equity'] - df['Equity'].cummax()) / df['Equity'].cummax()) *100
    max_drawdown_bench = ((df['Benchmark_Equity'] - df['Benchmark_Equity'].cummax()) / df['Benchmark_Equity'].cummax()) *100 

    plt.figure(figsize=(20, 6))
    dates = df.index
    
    plt.plot(dates, max_drawdown_strat, linewidth = 1, label='Strategy Drawdown')
    plt.fill_between(dates, max_drawdown_strat, 0, alpha=0.15)
    
    plt.plot(dates, max_drawdown_bench, linewidth = 1, label='Benchmark Drawdown')
    
    plt.axhline(0, linewidth=1)
    
    ax = plt.gca()
    locator = mpl_dates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    date_format = mpl_dates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_formatter(date_format)
    
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    
    plt.title('Strategy vs Benchmark Drawdown')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.show()

def plot_trades(df, trades_df, start_date=None, end_date=None):

    plot_df = df.loc[start_date:end_date]
    plot_trades = trades_df.copy()

    if start_date is not None:
        plot_trades = plot_trades[plot_trades['Entry_date'] >= start_date]

    if end_date is not None:
        plot_trades = plot_trades[plot_trades['Exit_date'] <= end_date]
    
    dates = plot_df.index
    price = plot_df['Close']
    entry_price = plot_trades['Entry_price']
    entry_date = plot_trades['Entry_date']
    exit_price = plot_trades['Exit_price']
    exit_date = plot_trades['Exit_date']
    
    plt.figure(figsize=(16,8))
    
    plt.plot(dates, price, linewidth=1, label='SPY Close')
    plt.scatter(entry_date, entry_price, marker='^', color='green', s=80, zorder=5, label='Entry')
    plt.scatter(exit_date, exit_price, marker='v', color='red', s=80, zorder=5, label='Exit')
    
    ax = plt.gca()
    locator = mpl_dates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    date_format = mpl_dates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_formatter(date_format)
    
    plt.xlabel('Dates')
    plt.ylabel('Price (USD)')
    plt.title('SPY Price with Strategy Trades')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()

def get_equity_curve_data(df):
    return {
        'dates': df.index.strftime('%Y-%m-%d').tolist(),
        'strategy_equity': df['Equity'].tolist(),
        'benchmark_equity': df['Benchmark_Equity'].tolist()
    }


def get_drawdown_data(df):
    strategy_drawdown = ((df['Equity'] / df['Equity'].cummax()) - 1) * 100

    benchmark_drawdown = ((df['Benchmark_Equity'] / df['Benchmark_Equity'].cummax()) - 1) * 100

    return {
        'dates': df.index.strftime('%Y-%m-%d').tolist(),
        'strategy_drawdown': strategy_drawdown.tolist(),
        'benchmark_drawdown': benchmark_drawdown.tolist()
    }