from src.strategies.base import Strategy
from datetime import datetime, time

class GoldBreakout(Strategy):
    def on_init(self):
        # Load Session Times
        sessions = self.config.get("TRADING_SESSION", {})
        
        # Parse times (Format "HH:MM")
        self.asian_start = self._parse_time(sessions.get("ASIAN_START", "03:30"))
        self.asian_end = self._parse_time(sessions.get("ASIAN_END", "13:30"))
        self.trade_end = self._parse_time(sessions.get("TRADE_END", "21:30"))
        
        # Strategy Params
        params = self.config.get("STRATEGY_PARAMS", {})
        self.tp_pips = params.get("TP_PIPS", 200)
        self.sl_pips = params.get("SL_PIPS", 100)
        self.trail_trigger = params.get("TRAIL_TRIGGER_PIPS", 20)
        self.trail_dist = params.get("TRAIL_DIST_PIPS", 5)
        
        # PIP Value for Gold (0.10 price diff = 1 pip usually, but let's stick to original)
        # Original: PIP_VAL_PRICE = 0.10
        self.PIP_VAL = 0.10
        
        # State
        self.asian_high = -1.0
        self.asian_low = float('inf')
        self.range_set = False

    def _parse_time(self, time_str):
        h, m = map(int, time_str.split(':'))
        return time(h, m)

    def next(self, candle):
        t = candle['time'].time()
        curr_high = candle['high']
        curr_low = candle['low']
        curr_close = candle['close']
        
        # Session Logic
        is_asian = (t >= self.asian_start) and (t < self.asian_end)
        is_trade = (t >= self.asian_end) and (t < self.trade_end)
        
        # 1. Define Range during Asian Session
        if t == self.asian_start:
            self.asian_high = curr_high
            self.asian_low = curr_low
            self.range_set = True
        elif is_asian:
            self.asian_high = max(self.asian_high, curr_high)
            self.asian_low = min(self.asian_low, curr_low)
            
        # 2. Reset Range if day over (or specific end time)
        if t >= self.trade_end:
            self.range_set = False

        # 3. Entry Logic (Only if no position)
        if self.position is None and is_trade and self.range_set:
            sl_dist_price = self.sl_pips * self.PIP_VAL
            tp_dist_price = self.tp_pips * self.PIP_VAL
            
            signal = None
            if curr_close > self.asian_high:
                # LONG Breakout
                entry_price = curr_close
                sl_price = entry_price - sl_dist_price
                tp_price = entry_price + tp_dist_price
                signal = 'long'
                
            elif curr_close < self.asian_low:
                # SHORT Breakout
                entry_price = curr_close
                sl_price = entry_price + sl_dist_price
                tp_price = entry_price - tp_dist_price
                signal = 'short'
                
            if signal:
                return self.signal_entry(signal, entry_price, sl_price, tp_price, comment="Breakout")
        
        # 4. Exit / Management Logic (if position exists)
        # handled by Engine usually, but if strategy has custom exit logic (like time exit)
        # The engine will check SL/TP. Strategy checks Time Exit.
        if self.position:
            if t >= self.trade_end:
                 return self.signal_exit(curr_close, reason="Session Close")
                 
            # Trailing Stop Logic could be here or in Engine.
            # Implemented in Engine in original, but better in Strategy if specific.
            # Let's emit a 'MODIFY_SL' signal or handle in Engine.
            # For simplicity, let's keep robust trailing in the Engine for now, 
            # or if the user wants it here:
            pass
            
        return None
