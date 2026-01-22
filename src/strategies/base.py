from abc import ABC, abstractmethod
import logging
from pathlib import Path

class Strategy(ABC):
    def __init__(self, config):
        self.config = config
        self.orders = []
        self.position = None # Current open position
        self.equity = config.get("initial_capital", 10000.0) # Tracked by engine usually, but local ref useful
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state_file = Path(config.get("PATHS", {}).get("STATE_FILE", "trade_state.pkl"))

    def save_state(self):
        """Save critical state to file."""
        import pickle
        state = {
            'orders': self.orders,
            'position': self.position,
            'equity': self.equity
        }
        # Allow child classes to add more state
        state.update(self.get_additional_state())
        
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump(state, f)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def load_state(self):
        """Load state from file."""
        import pickle
        if not self.state_file.exists():
            return False
            
        try:
            with open(self.state_file, 'rb') as f:
                state = pickle.load(f)
            
            self.orders = state.get('orders', [])
            self.position = state.get('position')
            self.equity = state.get('equity', self.equity)
            self.set_additional_state(state)
            self.logger.info("State loaded successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return False

    def get_additional_state(self):
        """Override to save custom strategy state."""
        return {}

    def set_additional_state(self, state):
        """Override to load custom strategy state."""
        pass

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
