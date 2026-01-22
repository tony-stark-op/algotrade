import logging
import sys
from src.config import config
from src.etl.loader import get_data_loader
from src.strategies.gold_breakout import GoldBreakout
from src.backtesting.engine import BacktestEngine
from src.backtesting.reporting import generate_report
from src.production.trader import LiveTrader

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("algotrade.log")
    ]
)
logger = logging.getLogger(__name__)

def main():
    mode = config.get("MODE", "BACKTESTING").upper()
    logger.info(f"Starting Application in {mode} mode.")
    
    try:
        loader = get_data_loader()
    except Exception as e:
        logger.error(f"Failed to setup data loader: {e}")
        return

    if mode == "BACKTESTING":
        # 1. Load Data
        start_date = datetime(2020, 1, 1) # Example default
        end_date = datetime.now()
        
        # We need raw data. 
        # If loader is MT5, it fetches. If CSV, it reads file.
        # But `fetch_data` arguments might differ or CSV just loads all.
        try:
             # CSV Loader ignores start/end if not filtered strictly, or we pass None to load all
             data = loader.fetch_data("XAUUSD", config.get("TIMEFRAME"), None, None)
        except Exception as e:
             logger.error(f"Data fetch failed: {e}")
             return

        if data.empty:
            logger.error("No data found. Please check data source.")
            return

        # 2. Run Backtest
        engine = BacktestEngine(GoldBreakout, data)
        trades, equity = engine.run()
        
        # 3. Report
        generate_report(trades, equity, engine.initial_capital)
        
    elif mode == "LIVE":
        trader = LiveTrader(GoldBreakout, loader)
        trader.run()
        
    else:
        logger.error(f"Invalid MODE: {mode}")

if __name__ == "__main__":
    from datetime import datetime
    main()
