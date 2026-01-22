from src.strategies.base import Strategy
from src.production.config import config as global_config
from datetime import datetime, time

class GoldBreakout(Strategy):
    def on_init(self):
        # 1. Load Session Times from YAML
        sessions = self.config.get("TRADING_SESSION", {})
        
        # User Time -> Broker Time
        self.asian_start = self._parse_and_convert(sessions.get("ASIAN_START", "03:30"))
        self.asian_end = self._parse_and_convert(sessions.get("ASIAN_END", "13:30"))
        self.trade_end = self._parse_and_convert(sessions.get("TRADE_END", "21:30"))
        
        # 2. Strategy Params
        params = self.config.get("STRATEGY_PARAMS", {})
        self.tp_pips = params.get("TP_PIPS", 200)
        self.sl_pips = params.get("SL_PIPS", 100)
        
        self.PIP_VAL = 0.10
        
        # 3. State
        self.asian_high = -1.0
        self.asian_low = float('inf')
        self.range_set = False
        
        # 4. Load Persistence Check
        # If user wants to resume, we assume we should load state
        # In a real app we might have a flag 'RESUME_SESSION' in config
        if global_config:  # Ensure we have access to global config helpers if needed
             self.load_state()

    def _parse_and_convert(self, time_str):
        """Parse string "HH:MM" (User TZ) and convert to Broker TZ."""
        h, m = map(int, time_str.split(':'))
        t = time(h, m)
        
        # If global config available, convert. Else raw time.
        if global_config:
            return global_config.convert_to_broker_time(t)
        return t

    def is_session_active(self, current_time, start_time, end_time):
        """Check if current_time is within [start_time, end_time), handling midnight crossover."""
        if start_time < end_time:
            return start_time <= current_time < end_time
        else:
            # Midnight crossover (e.g. 23:00 to 02:00)
            return current_time >= start_time or current_time < end_time

    def next(self, candle):
        t = candle['time'].time()
        curr_high = candle['high']
        curr_low = candle['low']
        curr_close = candle['close']
        
        # Session Logic using helper
        is_asian = self.is_session_active(t, self.asian_start, self.asian_end)
        is_trade = self.is_session_active(t, self.asian_end, self.trade_end)
        
        # 1. Define Range during Asian Session
        # Special check: If we just started script mid-session, we might not have 'exact start'
        # But for 'defining range', we usually want to track high/low continuously during Asian
        if is_asian:
            self.asian_high = max(self.asian_high, curr_high)
            self.asian_low = min(self.asian_low, curr_low)
            self.range_set = True
            
        # 2. Reset Range if day over (or specific end time)
        # Simple check: If NOT asian and NOT trade, reset
        # Or specifically if we pass trade_end.
        # Let's say if we are past Trade End and not in Asian.
        # But 'past' is tricky with midnight. 
        # Safer: If neither session is active, reset.
        if not is_asian and not is_trade and self.position is None:
             self.range_set = False
             self.asian_high = -1.0
             self.asian_low = float('inf')

        # 3. Entry Logic
        if self.position is None and is_trade and self.range_set:
            sl_dist_price = self.sl_pips * self.PIP_VAL
            tp_dist_price = self.tp_pips * self.PIP_VAL
            
            signal = None
            if curr_close > self.asian_high: # Long
                entry_price = curr_close
                sl_price = entry_price - sl_dist_price
                tp_price = entry_price + tp_dist_price
                signal = 'long'
                
            elif curr_close < self.asian_low: # Short
                entry_price = curr_close
                sl_price = entry_price + sl_dist_price
                tp_price = entry_price - tp_dist_price
                signal = 'short'
                
            if signal:
                self.save_state() # Save before entry attempt
                return self.signal_entry(signal, entry_price, sl_price, tp_price, comment="Breakout")
        
        # 4. Exit / Time Exit
        if self.position:
            # If trade session ended, close.
            if not is_trade:
                 return self.signal_exit(curr_close, reason="Session Close")
        
        # Periodically save state (e.g., every candle or on change)
        # To avoid IO spam, maybe only when values change significantly?
        # For safety, saving every step is okay for small scale.
        # self.save_state() 
        return None

    def get_additional_state(self):
        return {
            'asian_high': self.asian_high,
            'asian_low': self.asian_low,
            'range_set': self.range_set
        }

    def set_additional_state(self, state):
        self.asian_high = state.get('asian_high', -1.0)
        self.asian_low = state.get('asian_low', float('inf'))
        self.range_set = state.get('range_set', False)

