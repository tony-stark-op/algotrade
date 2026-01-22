import time
import logging
import pytz
from datetime import datetime, timedelta, time as dtime
import pandas as pd
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
        self.user_tz = pytz.timezone(config.get("TIMEZONE", {}).get("USER", "Asia/Kolkata"))
        
    def run(self):
        logger.info("Starting Live Trader...")
        if not self.loader.initialize():
            logger.error("Failed to initialize Data Loader (MT5).")
            return
            
        # Initialize Strategy
        self.strategy.on_init()
        
        # --- 1. Historical Catch-up ---
        logger.info("Syncing historical state...")
        self.sync_state()
        
        # --- 2. Main Loop ---
        logger.info("Live loop running... (Ctrl+C to stop)")
        try:
            last_candle_time = None
            
            while True:
                # Sleep to avoid hammering CPU
                time.sleep(1) 
                
                # Check for new candle
                # Logic: Get last completed candle. 
                # If 'time' of last completed candle > last_seen, process it.
                
                # Fetch recent data (e.g. last 2 candles)
                # We want the latest CLOSED candle.
                # MT5 copy_rates_from_pos(..., 2) -> returns current (forming) and previous (closed)
                
                # Using loader's generic interface is harder for "last 2 candles" without overhead.
                # Let's use direct MT5 calls if loader allows, or just fetch small time range.
                
                # Optimization: MT5 specific
                if config.get("DATALOADING") in ["LIVE", "HISTORY"]: 
                    # Direct efficient call
                    # copy_rates_from_pos(symbol, timeframe, start_pos, count)
                    # pos 0 is current, pos 1 is last closed
                    if not mt5: break 
                    
                    tf_map = {
                        "M1": mt5.TIMEFRAME_M1, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1
                    }
                    tf = tf_map.get(self.timeframe_str, mt5.TIMEFRAME_M15)
                    
                    # Fetch last 2 candles
                    rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, 2)
                    if rates is None: continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    
                    # The candle at index 0 (if len=2) is the previous closed one [0, 1] -> 0 is older?
                    # copy_rates_from_pos: "The elements are ordered from the past to the present"
                    # So rates[-1] is current (forming), rates[-2] is last closed.
                    last_closed = df.iloc[-2]
                    
                    ts = last_closed['time']
                    
                    if last_candle_time is None or ts > last_candle_time:
                        logger.info(f"New Candle Detected: {ts}")
                        last_candle_time = ts
                        
                        # Process Candle
                        # Standardize format
                        # We need 'open', 'high', 'low', 'close', 'time'
                        # MT5 DF has lowercase cols usually.
                        candle_data = {
                            'time': ts, # This is usually UTC or Server Time.
                            # We might need to convert this 'time' to User/Broker correct TZ 
                            # if the strategy expects 'time' column to be timezone aware?
                            # The strategy uses .dt.time() on it. 
                            # Our loader usually converts.
                            'open': last_closed['open'],
                            'high': last_closed['high'],
                            'low': last_closed['low'],
                            'close': last_closed['close']
                            'close': last_closed['close']
                        }
                        
                        # Log Current Price periodically (e.g. every 10s) to show life
                        # Timestamp of 'ts' is when candle closed. 
                        # We might want REAL time price? 
                        # 'last_closed' is 15 mins ago if no new candle.
                        # Actually we want 'current price' which is the CLOSE of the *forming* candle (index -1)
                        # We fetched 2 candles: [Closed, Forming]. 
                        # Let's get the forming candle for price display.
                        
                        # Note: Logic above used last_closed for strategy. 
                        # Here we just log for user.
                        # But wait, we are inside `if last_candle_time is None or ts > last_candle_time:`
                        # This block only runs once per 15 mins!
                        # We need to move the logging OUTSIDE this block if we want it frequently.
                        
                        signal = self.strategy.next(candle_data)
                        
                        if signal:
                           logger.info(f"SIGNAL GENERATED: {signal}")
                           self._execute_order(signal)
                           
                else:
                    pass

                # --- Heartbeat / Price Log (Every ~15 seconds) ---
                if int(time.time()) % 15 == 0:
                     if mt5:
                         tick = mt5.symbol_info_tick(self.symbol)
                         if tick:
                            logger.info(f"[{self.symbol}] Current Price: {tick.bid} / {tick.ask}")


        except KeyboardInterrupt:
            logger.info("Stopping Live Trader...")
        finally:
            self.loader.shutdown()

    def sync_state(self):
        """Fetch data from start of 'today' (Asian Start) to now and replay strategy."""
        now = datetime.now(self.user_tz)
        today_open = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # We might need yesterday if Asian session starts late previous day? 
        # For GoldBreakout, Asian starts 03:30 (typical).
        # So fetching from 00:00 Today is safe.
        
        # Convert to 'start_dt' for fetch_data.
        # fetch_data expects datetime.
        start_dt = today_open
        end_dt = now
        
        logger.info(f"Fetching history from {start_dt} to {end_dt}...")
        df = self.loader.fetch_data(self.symbol, self.timeframe_str, start_dt, end_dt)
        
        if df.empty:
            logger.warning("No historical data found for today. Starting fresh.")
            return

        logger.info(f"Replaying {len(df)} candles...")
        records = df.to_dict('records')
        for candle in records:
            # We don't execute orders during replay, just update state
            self.strategy.next(candle)  
            
        # Sync complete
        state = self.strategy.get_additional_state()
        logger.info(f"State Synced: Asian High={state.get('asian_high')}, Low={state.get('asian_low')}")

    def _execute_order(self, signal):
        """Execute orders via MT5"""
        if not mt5: return
        
        action = signal.get('action') # ENTRY or EXIT
        if action == 'ENTRY':
            type_str = signal.get('type') # long or short
            price = signal.get('price')
            sl = signal.get('sl')
            tp = signal.get('tp')
            
            # 1. Calc Volume
            # Use Fixed for now or calc based on Risk
            # self.strategy.calculate_lots might be useful but likely needs Account Info
            # Simple Fixed Lot from Config
            volume = config.get("FIXED_LOT_SIZE", 0.01)
            
            # 2. Prepare Request
            order_type = mt5.ORDER_TYPE_BUY if type_str == 'long' else mt5.ORDER_TYPE_SELL
            
            # We usually send MARKET orders if 'price' is close to current.
            # Or PENDING? Breakout usually implies Stop Order.
            # But strategy logic fires when "Close > High". So connection is happening. 
            # So Market Execution is appropriate.
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": float(volume),
                "type": order_type,
                "price": price, # For Market, this is reference. MT5 uses current Ask/Bid
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 123456,
                "comment": "GoldBreakoutBot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Adjust Price for filling
            # For Buy, we ask. For Sell, we bid.
            # tick = mt5.symbol_info_tick(self.symbol)
            # if type_str == 'long': request['price'] = tick.ask
            # else: request['price'] = tick.bid
            
            logger.info(f"Sending Order: {type_str} {volume} Lots @ {price} | SL: {sl} TP: {tp}")
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order Failed: {result.comment} ({result.retcode})")
            else:
                logger.info(f"Order Executed: {result.order}")
                
                # Update Strategy Logic that we have a position?
                # The strategy class has self.position. 
                # Ideally, we should sync this from MT5 events, 
                # but for now we manually set it to stop duplicate signals.
                self.strategy.position = {'ticket': result.order}
                
        elif action == 'EXIT':
            # Close position
            # We need ticket. 
            # Strategy might not know ticket if we just restarted.
            # We should scan open positions for this symbol/magic.
            pass
