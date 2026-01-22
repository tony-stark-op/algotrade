# AlgoTrade OOPS Refactoring Framework

The project has been successfully refactored into a modular Object-Oriented framework.

## Project Structure

The codebase is now organized into specialized modules:
- `src/etl`: Data loading (MT5 & Custom CSV).
- `src/strategies`: Trading logic (Base Strategy & Gold Breakout).
- `src/backtesting`: Backtest Engine & Reporting.
- `src/production`: Live Trading Engine.
- `config.json`: Centralized configuration.
- `main.py`: Entry point.

## Configuration (`config.json`)

You can control the entire application via `config.json`.
- **Mode**: `BACKTESTING` or `LIVE`.
- **Data Loading**: `LIVE` (MT5), `HISTORY` (MT5), or `CUSTOM` (CSV).
- **Risk Management**: `DYNAMIC` (% Risk) or `STATIC` (Fixed Lots).

## Usage

### Prerequisites
Install dependencies:
```bash
pip install -r requirements.txt
```
*(Note: `MetaTrader5` package is required for LIVE/HISTORY modes)*

### Running a Backtest
1. Edit `config.json`:
   ```json
   "MODE": "BACKTESTING",
   "DATALOADING": "CUSTOM", // or "HISTORY"
   "DATA_FILE_PATH": "dummy_data.csv"
   ```
2. Run:
   ```bash
   python main.py
   ```
3. Check `trades.csv` and `report.txt` for results.

### Running Live Trading
1. Open MT5 Terminal.
2. Edit `config.json`:
   ```json
   "MODE": "LIVE",
   "DATALOADING": "LIVE"
   ```
3. Run:
   ```bash
   python main.py
   ```

## Verification
A `dummy_data.csv` has been created for testing. The current `config.json` is set to run a backtest on this dummy data.

## Features
- **Abstract Strategy**: Easily add new strategies by inheriting from `src.strategies.base.Strategy`.
- **Flexible ETL**: Switch between MT5 and CSV data without changing code.
- **Enhanced Reporting**: Reports now include Win Rate, Profit Factor, Drawdown, and Sortino/SQN metrics.
