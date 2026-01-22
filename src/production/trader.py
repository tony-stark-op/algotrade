import time
import logging
import pytz
from datetime import datetime
from src.config import config
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

logger = logging.getLogger(__name__)

class LiveTrader:
    def __init__(self, strategy_cls, data_loader):
        self.strategy = strategy_cls(config)
        self.loader = data_loader
        self.symbol = "XAUUSD" # Configurable?
        self.timeframe_str = config.get("TIMEFRAME", "M15")
        
    def run(self):
        logger.info("Starting Live Trader...")
        if not self.loader.initialize():
            logger.error("Failed to initialize Data Loader (MT5).")
            return
            
        self.strategy.on_init()
        
        # Main Loop
        try:
            while True:
                # 1. Fetch latest candle
                # We need the completed candle, so we look for the one that just closed?
                # or we run on every tick?
                # Original strategy runs on 'candles'. So we wait for new candle or check periodically.
                
                # Simple loop: sleep 10s, check if new candle.
                
                # Get last 2 candles to ensure we have the closed one.
                # start = datetime.now() - timedelta
                # For simplicity, let's just fetch recent history.
                
                # In real prod, this needs robust logic (OnTick vs OnTimer).
                # Here we simulate a loop.
                
                logger.info("Live loop running... (Ctrl+C to stop)")
                time.sleep(60) 
                
                # Placeholder for real logic:
                # 1. Get Data
                # df = self.loader.fetch_data(...)
                # 2. candle = df.iloc[-1]
                # 3. signal = self.strategy.next(candle)
                # 4. Execute Signal via MT5 OrderSend
                
        except KeyboardInterrupt:
            logger.info("Stopping Live Trader...")
        finally:
            self.loader.shutdown()

    def _execute_order(self, signal):
        # Translate Strategy Signal to MT5 Order
        pass
