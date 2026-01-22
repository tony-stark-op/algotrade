import logging
import sys
from src.config import config
from src.etl.loader import get_data_loader
from src.strategies.gold_breakout import GoldBreakout
from src.production.trader import LiveTrader

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("system.log")
    ]
)
logger = logging.getLogger("Main")

def main():
    mode = config.get("MODE", "LIVE").upper()
    logger.info(f"Initializing AlgoTrader in {mode} mode...")
    
    if mode == "BACKTESTING":
        logger.warning("Config is set to BACKTESTING.")
        logger.warning("Please run the dedicated backtest script for simulation:")
        logger.warning("  python3 run_gold_breakout.py")
        return

    elif mode == "LIVE":
        try:
            loader = get_data_loader()
            trader = LiveTrader(GoldBreakout, loader)
            trader.run()
        except Exception as e:
            logger.critical(f"Runtime Error: {e}", exc_info=True)
        
    else:
        logger.error(f"Invalid MODE configured: {mode}")

if __name__ == "__main__":
    main()
