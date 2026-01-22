import sys
import logging
from pathlib import Path
import pandas as pd

# Ensure src in path
sys.path.append(str(Path(__file__).parent.parent))

from src.production.config import config
from src.etl.loader import get_data_loader
from src.strategies.gold_breakout import GoldBreakout
from src.backtesting.engine import BacktestEngine
from src.utils.results import ResultManager

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RunBacktest")

def main():
    logger.info("Initializing Backtest...")
    
    # 1. Reload Config ensure fresh state
    config.reload()
    
    # Check Mode
    if config.get("MODE") != "BACKTESTING":
        logger.error("Config MODE is not 'BACKTESTING'. Please update config.")
        sys.exit(1)

    # 2. Load Data
    try:
        loader = get_data_loader()
        # Dates could be parametric, for now all
        df = loader.fetch_data(symbol="XAUUSD", timeframe_str=config.get("TIMEFRAME"), start_dt=None, end_dt=None)
        logger.info(f"Loaded {len(df)} candles.")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        sys.exit(1)
        
    if df.empty:
        logger.error("No data found.")
        sys.exit(1)

    # 3. Initialize Result Manager
    rm = ResultManager(strategy_name="GoldBreakout")
    
    # 4. Run Engine
    try:
        engine = BacktestEngine(GoldBreakout, df)
        trades_df, equity_df = engine.run()
        
        # 5. Metrics & Saving
        metrics = generate_metrics(trades_df, engine.initial_capital, engine.equity)
        
        rm.save_trades(trades_df.to_dict('records'))
        rm.save_performance(metrics)
        
        logger.info(f"Backtest Complete. Results saved to {rm.get_run_dir()}")
        print(f"SUCCESS: Results saved to {rm.get_run_dir()}") # Marker for dashboard
        
    except Exception as e:
        logger.error(f"Backtest Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def generate_metrics(trades_df, initial, final):
    if trades_df.empty:
        return {"total_trades": 0, "net_profit": 0.0}
        
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    
    n_wins = len(wins)
    win_rate = (n_wins / total_trades) * 100
    
    net_profit = final - initial
    
    metric = {
        "initial_balance": initial,
        "final_balance": final,
        "net_profit": net_profit,
        "return_pct": (net_profit / initial) * 100,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "wins": n_wins,
        "losses": len(losses)
    }
    return metric

if __name__ == "__main__":
    main()
