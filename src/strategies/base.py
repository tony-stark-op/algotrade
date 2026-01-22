from abc import ABC, abstractmethod
import logging

class Strategy(ABC):
    def __init__(self, config):
        self.config = config
        self.orders = []
        self.position = None # Current open position
        self.equity = config.get("initial_capital", 10000.0) # Tracked by engine usually, but local ref useful
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def on_init(self):
        """Called before the strategy starts."""
        pass

    @abstractmethod
    def next(self, candle):
        """Called for every new candle."""
        pass
        
    def signal_entry(self, direction, price, sl, tp, comment=""):
        """
        Generates an entry signal.
        direction: 'long' or 'short'
        """
        return {
            'action': 'ENTRY',
            'type': direction,
            'price': price,
            'sl': sl,
            'tp': tp,
            'comment': comment
        }
    
    def signal_exit(self, price, reason=""):
        """Generates an exit signal."""
        return {
            'action': 'EXIT',
            'price': price,
            'reason': reason
        }

    def calculate_lots(self, entry_price, sl_price):
        """
        Calculates lot size based on config (Dynamic Risk or Fixed Lots).
        """
        mode = self.config.get("RISK_MANAGEMENT", "DYNAMIC")
        
        if mode == "STATIC":
            return self.config.get("FIXED_LOT_SIZE", 0.01)
        
        elif mode == "DYNAMIC":
            risk_pct = self.config.get("RISK_PERCENTAGE", 1.0) / 100.0
            risk_amt = self.equity * risk_pct
            
            # Pip Value & SL Distance
            # Assuming XAUUSD 1 Pip = 0.10 Price change = $10 per lot (standard)?
            # User original code: 1 Pip = 0.10 PRICE. 
            # 1 Lot ($1 move) = $100 Profit.
            # So Risk = SL_Dist_Price * 100 * Lots
            # Lots = Risk / (SL_Dist_Price * 100)
            
            sl_dist = abs(entry_price - sl_price)
            if sl_dist == 0: return 0.01
            
            lots = risk_amt / (sl_dist * 100.0)
            lots = round(lots, 2)
            return max(lots, 0.01)
            
        return 0.01
