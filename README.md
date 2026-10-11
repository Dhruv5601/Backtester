# Quant Backtester

A Python-based quantitative backtesting application for evaluating a moving-average crossover strategy against a buy-and-hold benchmark. The project combines historical market data, performance analytics, interactive visualizations, and PDF reporting in a Flask web dashboard.

## Overview

The goal of Quant Backtester is to make systematic trading strategy evaluation accessible and reproducible. Users can select a supported stock or ETF, choose a historical period or custom date range, and compare the strategy's performance with the underlying asset.

## Features

- **Multiple assets:** SPY, AAPL, MSFT, NVDA, AMZN, TSLA, GOOGL, and META.
- **Custom date ranges:** Evaluate selected historical periods with warm-up data for moving-average calculations.
- **Moving-average crossover:** A long-only strategy using 20-day and 50-day simple moving averages.
- **Performance analytics:** Total return, CAGR, annualized volatility, maximum drawdown, Sharpe ratio, and Sortino ratio.
- **Trade statistics:** Win rate, average win/loss, profit factor, expectancy, trade duration, and winning/losing streaks.
- **Visualizations:** Strategy-versus-benchmark equity curves and drawdown charts.
- **PDF reports:** Export performance summaries, risk metrics, trade analysis, and execution details.

## Strategy Methodology

The strategy generates a buy signal when the 20-day simple moving average crosses above the 50-day moving average and a sell signal when it crosses below.

- Long-only: the strategy holds either a long position or cash.
- Execution: signals generated at a daily close are executed at the following trading session's open.
- Transaction costs: 0.05% per side.
- Benchmark: buy-and-hold performance of the selected asset.
- Initial capital: $100,000 by default.

The application uses historical price data and calculates performance from the resulting equity curve. Backtest results depend on the selected asset, period, data, and execution assumptions.

## Historical Case Study: META

In the October 10, 2016–October 9, 2026 backtest, the 20/50-day moving-average strategy produced a 571.58% total return, compared with 451.80% for the buy-and-hold benchmark.

| Metric | Strategy | Benchmark |
|---|---:|---:|
| Total return | 571.58% | 451.80% |
| CAGR | 20.99% | 18.63% |
| Annualized volatility | 27.40% | 39.54% |
| Maximum drawdown | −34.87% | −76.74% |
| Sharpe ratio | 0.83 | 0.63 |
| Sortino ratio | 1.34 | 0.91 |

These results are specific to this historical test and do not establish future performance or guarantee that the strategy will outperform on other assets or periods.

## Getting Started

### Requirements

- Windows
- Python
- Internet access to retrieve historical market data

### Run the Application

1. Clone or download this repository.
2. Open the project folder.
3. Run `run.bat`.
4. Follow any setup prompts and open the local dashboard address displayed in the terminal.

If the launcher successfully creates the virtual environment, installs dependencies, and starts Flask, no separate manual installation should be necessary.

## Technology Stack

- Python
- Flask
- pandas and NumPy
- yfinance
- Matplotlib / ReportLab
- Chart.js

## Limitations

- Historical backtests are not predictions of future returns.
- Results depend on data quality, trading assumptions, and transaction-cost estimates.
- The strategy does not model every real-world trading friction, including all possible slippage, liquidity constraints, taxes, or broker-specific fees.
- The project is intended for research and educational use, not as financial advice.

## Disclaimer

Quant Backtester is an educational research tool. Backtest results are hypothetical and do not guarantee future investment performance. Users should independently evaluate the methodology and assumptions before relying on any results.
