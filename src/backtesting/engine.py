import pandas as pd
import logging
from src.config import config

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, strategy_cls, data):
        self.strategy = strategy_cls(config)
        self.data = data
        self.trades = []
        self.equity_curve = []
        
        self.initial_capital = config.get("initial_capital", 10000.0)
        self.equity = self.initial_capital
        
        # Trailing Stop Config from Strategy Params
        params = config.get("STRATEGY_PARAMS", {})
        self.trail_trigger = params.get("TRAIL_TRIGGER_PIPS", 20) * 0.10
        self.trail_dist = params.get("TRAIL_DIST_PIPS", 5) * 0.10
        
    def run(self):
        logger.info(f"Starting Backtest on {len(self.data)} records...")
        
        self.strategy.on_init()
        self.strategy.equity = self.equity # Sync equity
        
        df = self.data.reset_index(drop=True)
        records = df.to_dict('records') # Fast iteration
        
        for candle in records:
            # Update Strategy Equity
            self.strategy.equity = self.equity
            current_time = candle['time']
            
            # 1. Manage Existing Position
            if self.strategy.position:
                self._manage_position(candle)
                
            # 2. Run Strategy Logic (Generating Signals)
            signal = self.strategy.next(candle)
            
            # 3. Process Signals
            if signal:
                if signal['action'] == 'ENTRY':
                    if not self.strategy.position:
                        self._execute_entry(signal, candle)
                elif signal['action'] == 'EXIT':
                    if self.strategy.position:
                        self._execute_exit(signal['price'], signal['reason'], candle)
                        
            # Record Equity (approximate, at close of candle)
            # Ideally verify if trade closed this candle to update equity
            self.equity_curve.append({
                'time': current_time,
                'equity': self.equity
            })
            
        logger.info("Backtest Completed.")
        return pd.DataFrame(self.trades), pd.DataFrame(self.equity_curve)

    def _execute_entry(self, signal, candle):
        # Calculate Lots if not provided or calc by strategy
        lots = self.strategy.calculate_lots(signal['price'], signal['sl'])
        
        position = {
            'type': signal['type'],
            'entry_time': candle['time'],
            'entry_price': signal['price'],
            'sl': signal['sl'],
            'tp': signal['tp'],
            'size': lots,
            'peak_price': signal['price'] # For tracking trailing
        }
        self.strategy.position = position
        # logger.info(f"ENTRY {signal['type']} @ {signal['price']} (Lots: {lots})")

    def _execute_exit(self, price, reason, candle):
        pos = self.strategy.position
        if not pos: return
        
        # Calculate PnL
        # PnL = PriceDiff * 100 * Lots (Standard XAUUSD assumption from original)
        if pos['type'] == 'long':
            diff = price - pos['entry_price']
        else:
            diff = pos['entry_price'] - price
            
        pnl = diff * 100.0 * pos['size']
        
        self.equity += pnl
        
        trade_record = {
            'entry_time': pos['entry_time'],
            'exit_time': candle['time'],
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': price,
            'size': pos['size'],
            'pnl': pnl,
            'reason': reason,
            'equity_after': self.equity
        }
        self.trades.append(trade_record)
        self.strategy.position = None
        # logger.info(f"EXIT {pos['type']} @ {price} | PnL: {pnl:.2f} | {reason}")

    def _manage_position(self, candle):
        pos = self.strategy.position
        if not pos: return
        
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        exit_price = None
        exit_reason = ""
        
        # Check SL/TP
        if pos['type'] == 'long':
            if low <= pos['sl']:
                exit_price = pos['sl'] # Assume slippage? No, keep simple
                exit_reason = "SL"
            elif high >= pos['tp']:
                exit_price = pos['tp']
                exit_reason = "TP"
            else:
                # Trailing Stop Logic
                # If High > Entry + Trigger
                if high > pos['peak_price']:
                    pos['peak_price'] = high # Update peak
                    
                trigger_level = pos['entry_price'] + self.trail_trigger
                if high >= trigger_level:
                    # New SL = CurrentHigh - Dist
                    new_sl = high - self.trail_dist
                    if new_sl > pos['sl']:
                        pos['sl'] = new_sl
                        # logger.debug(f"Adjusted SL to {new_sl}")

        else: # Short
            if high >= pos['sl']:
                exit_price = pos['sl']
                exit_reason = "SL"
            elif low <= pos['tp']:
                exit_price = pos['tp']
                exit_reason = "TP"
            else:
                # Trailing Stop Logic
                if low < pos['peak_price']:
                    pos['peak_price'] = low
                    
                trigger_level = pos['entry_price'] - self.trail_trigger
                if low <= trigger_level:
                    # New SL = CurrentLow + Dist
                    new_sl = low + self.trail_dist
                    if new_sl < pos['sl']:
                        pos['sl'] = new_sl

        if exit_price:
            self._execute_exit(exit_price, exit_reason, candle)
