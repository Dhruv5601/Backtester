import pandas as pd

def calculate_performance(df, initial_capital=100000):

    first_day = df.index.min()
    last_day = df.index.max()
    duration_years = (last_day - first_day).days / 365.2425

    current_equity = df.iloc[-1]['Equity']
    benchmark_equity = df.iloc[-1]['Benchmark_Equity']

    equity_return = ((current_equity - initial_capital) / initial_capital)*100
    benchmark_return = ((benchmark_equity - initial_capital) / initial_capital)*100

    cagr_equity = (((current_equity/initial_capital)**(1/duration_years)) - 1)*100
    cagr_benchmark_equity = (((benchmark_equity/initial_capital)**(1/duration_years)) - 1)*100

    strat_volatility, benchmark_volatility = volatility(df)
    strat_drawdown, bench_drawdown = max_drawdown(df)
    strat_sharpe, bench_sharpe = sharpe_ratio(df)
    start_sortino, bench_sortino = sortino_ratio(df)

    dict1 = {
        'Strategy': [
            f'{equity_return:.2f}%',
            f'{cagr_equity:.2f}%',
            f'{strat_volatility:.2f}%',
            f'{strat_drawdown:.2f}%',
            f'{strat_sharpe:.2f}',
            f'{start_sortino:.2f}'
            ],
        'Benchmark': [
            f'{benchmark_return:.2f}%',
            f'{cagr_benchmark_equity:.2f}%',
            f'{benchmark_volatility:.2f}%',
            f'{bench_drawdown:.2f}%',
            f'{bench_sharpe:.2f}',
            f'{bench_sortino:.2f}'
            ],
        'Performance':['Total Return','CAGR','Volatility','Max drawdown','Sharpe Ratio','Sortino Ratio']}
    return dict1


def volatility(df):

    strat_std = df['Strategy_Return'].std()
    strat_volatility = (strat_std)*(252**0.5) *100
    benchmark_std = df['Benchmark_Return'].std() 
    benchmark_volatility = (benchmark_std)*(252**0.5) *100
    return strat_volatility, benchmark_volatility

def max_drawdown(df):
    max_drawdown_strat = ((df['Equity'] - df['Equity'].cummax()) / df['Equity'].cummax()).min() *100
    max_drawdown_bench = ((df['Benchmark_Equity'] - df['Benchmark_Equity'].cummax()) / df['Benchmark_Equity'].cummax()).min() *100
    return max_drawdown_strat, max_drawdown_bench


def sharpe_ratio(df, risk_free_rate= 0.0):
    daily_risk_free = (1 + risk_free_rate)**(1/252) - 1
    strat_daily_ret = df['Strategy_Return'].mean()
    bench_daily_ret = df['Benchmark_Return'].mean()
    sharpe_strat = ((strat_daily_ret - daily_risk_free) / df['Strategy_Return'].std() ) * ((252)**0.5)
    sharpe_bench = ((bench_daily_ret - daily_risk_free) / df['Benchmark_Return'].std()  ) * ((252)**0.5)
    return sharpe_strat, sharpe_bench

def sortino_ratio(df, MAR= 0.0):
    daily_MAR = (1 + MAR)**(1/252) - 1
    strat_daily_ret = df['Strategy_Return'].mean()
    bench_daily_ret = df['Benchmark_Return'].mean()

    relative_down_ret = df['Strategy_Return'] - daily_MAR
    relative_down_ret2 = df['Benchmark_Return'] - daily_MAR

    relative_down_ret.loc[relative_down_ret > 0] = 0
    relative_down_ret2.loc[relative_down_ret2 > 0] = 0

    strat_downside_deviation = (((relative_down_ret**2).mean()) ** 0.5) * (252**0.5)
    bench_downside_deviation = (((relative_down_ret2**2).mean()) ** 0.5) * (252**0.5)

    annual_strat_return = strat_daily_ret * 252
    annual_bench_return = bench_daily_ret * 252

    sortino_strat = (annual_strat_return - MAR)/ strat_downside_deviation
    sortino_bench = (annual_bench_return - MAR)/ bench_downside_deviation
    return sortino_strat, sortino_bench

def calculate_trade_statistics(trades_df):
    total_trades = len(trades_df)
    winning_trades = len(trades_df.loc[(trades_df['Net_return']) > 0])
    losing_trades = len(trades_df.loc[(trades_df['Net_return']) < 0])
    break_even_trades = len(trades_df.loc[(trades_df['Net_return']) == 0])

    if total_trades == 0:
        win_rate = 0
        loss_rate = 0
    else:
        win_rate = (winning_trades) / total_trades *100
        loss_rate = (losing_trades) / total_trades * 100

    if winning_trades == 0:
        avg_win = 0
    else:
        avg_win = trades_df.loc[(trades_df['Net_return'] > 0), 'Net_return'].sum() / (winning_trades) *100

    if losing_trades == 0:
        avg_loss = 0
        profit_factor = float('inf')
    else:
        avg_loss = trades_df.loc[(trades_df['Net_return'] < 0), 'Net_return'].sum() / (losing_trades) *100
        profit_factor = (trades_df.loc[(trades_df['Net_return'] > 0), 'Net_return'].sum()) / abs(trades_df.loc[(trades_df['Net_return'] < 0), 'Net_return'].sum())
        
    if total_trades == 0:
        best_trade = pd.DataFrame()
        worst_trade = pd.DataFrame()
    else:
        best_trade = trades_df.loc[(trades_df['Net_return'] == trades_df['Net_return'].max())].copy()
        worst_trade = trades_df.loc[(trades_df['Net_return'] == trades_df['Net_return'].min())].copy()

    expectancy = ((win_rate/100) * avg_win) + ((loss_rate/100) * avg_loss)

    adder = 0
    winstreak_list = []
    losingstreak_list = []
    winstreak_count = 0
    losingstreak_count = 0

    if total_trades == 0:
        winstreak_list.append(0)
        losingstreak_list.append(0)
        avg_trade_duration = 0
        median_trade_duration = 0
    else:
    
        trade_durations = trades_df['Exit_date'] - trades_df['Entry_date']
        avg_trade_duration = (trade_durations).mean() / pd.Timedelta(days=1)
        median_trade_duration = (trade_durations).median() / pd.Timedelta(days=1)
        
        while adder < total_trades:
            if trades_df.iloc[adder]['Net_return'] == 0:
                winstreak_count = 0
                losingstreak_count = 0
                
            if trades_df.iloc[adder]['Net_return'] > 0:
                winstreak_count += 1
            elif trades_df.iloc[adder]['Net_return'] < 0:
                if winstreak_count > 0:
                    winstreak_list.append(winstreak_count)
                winstreak_count = 0
        
            if trades_df.iloc[adder]['Net_return'] < 0:
                losingstreak_count += 1
            elif trades_df.iloc[adder]['Net_return'] > 0:
                if losingstreak_count > 0:
                    losingstreak_list.append(losingstreak_count)
                losingstreak_count = 0
                
            adder += 1
        
        if winstreak_count > 0:
            winstreak_list.append(winstreak_count)
        
        if losingstreak_count > 0:
            losingstreak_list.append(losingstreak_count)

    best_trade.reset_index(inplace=True)
    worst_trade.reset_index(inplace=True)

    best_trade['Type'] = 'Best Trade'
    worst_trade['Type'] = 'Worst Trade'

    trade_performance = pd.concat([best_trade, worst_trade])
    trade_performance.set_index('Type', inplace=True)

    dict2 = {'Statistics': [total_trades,winning_trades,losing_trades,break_even_trades,f'{win_rate:.2f}%',f'{avg_win:.2f}%',f'{abs(avg_loss):.2f}%',profit_factor,f'{expectancy:.2f}%',f'{avg_trade_duration:.2f} days',f'{median_trade_duration:.2f} days',max(winstreak_list),max(losingstreak_list)],
             'Benchmark': ['Total Trades','Winning Trades', 'Losing Trades','Break Even Trades','Win Rate','Average Win','Average Loss','Profit Factor', 'Expectancy','Average Trade Duration','Median Trade Duration','Longest Winning Streak','Longest Losing Streak']}
    return dict2,trade_performance