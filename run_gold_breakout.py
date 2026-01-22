import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time, timedelta
import logging
from pathlib import Path
import matplotlib.pyplot as plt

# --- Configuration ---
DATA_PATH = Path("src/mt5_data/XAUUSD15.csv")
OUTPUT_TRADES_PATH = Path("breakout_trades.csv")
OUTPUT_EQUITY_PATH = Path("breakout_equity.csv")
OUTPUT_PLOT_PATH = Path("breakout_curve.png")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_user_inputs():
    print("\n--- Backtest Configuration ---")
    
    # Initial Capital
    try:
        cap_str = input("Enter Initial Capital (Default 10000): ").strip()
        initial_capital = float(cap_str) if cap_str else 10000.0
    except ValueError:
        print("Invalid input, using default 10000.")
        initial_capital = 10000.0
        
    # Risk Mode
    print("\n--- Position Sizing ---")
    print("1. Risk Percentage per Trade (e.g., 1%)")
    print("2. Fixed Lot Size (e.g., 0.1 Lots)")
    mode_input = input("Select Mode (1 or 2, Default 1): ").strip()
    
    risk_pct = 0.01
    fixed_lots = 0.0
    mode = 'risk'
    
    if mode_input == '2':
        mode = 'fixed'
        try:
            lot_str = input("Enter Fixed Lot Size (e.g., 0.1): ").strip()
            fixed_lots = float(lot_str) if lot_str else 0.1
        except ValueError:
            print("Invalid input, using default 0.1 lots.")
            fixed_lots = 0.1
    else:
        try:
            risk_str = input("Enter Risk Percentage (e.g., 1 for 1%): ").strip()
            risk_pct = (float(risk_str) / 100.0) if risk_str else 0.01
        except ValueError:
            print("Invalid input, using default 1%.")
            risk_pct = 0.01

    # Duration
    print("\n--- Backtest Duration ---")
    try:
        dur_str = input("Enter Duration in Months (0 for All, e.g. 12 for last year): ").strip()
        duration_months = int(dur_str) if dur_str else 0
    except ValueError:
        print("Invalid input, using 0 (All Data).")
        duration_months = 0
        
    if duration_months < 0: duration_months = 0

    inputs = {
        'initial_capital': initial_capital,
        'mode': mode,
        'risk_pct': risk_pct,
        'fixed_lots': fixed_lots,
        'tp_pips': 200,
        'sl_pips': 100,
        'trail_trigger': 20, # Pips
        'trail_dist': 5,      # Pips
        'duration_months': duration_months
    }
    return inputs

def load_data(path):
    logger.info(f"Loading data from {path}...")
    # Read CSV: Time, Open, High, Low, Close, Vol
    df = pd.read_csv(path, sep='\t', header=None, 
                     names=["time_str", "open", "high", "low", "close", "vol"])
    
    # Parse Time
    logger.info("Parsing timestamps...")
    df['time'] = pd.to_datetime(df['time_str'])
    
    # Timezone Conversion: Server (Athens) -> IST
    src_tz = pytz.timezone('Europe/Athens')
    dst_tz = pytz.timezone('Asia/Kolkata')
    
    # Vectorized TZ conversion (approximate for speed, usually accurately enough for backtest range)
    # Note: 'ambiguous' handling might drop DST switch hour
    try:
        df['time_ist'] = df['time'].dt.tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='shift_forward').dt.tz_convert('Asia/Kolkata')
    except Exception:
        # Fallback to slow apply if vectorized fails hard
        def convert_tz(dt):
            try: return src_tz.localize(dt).astimezone(dst_tz)
            except: return src_tz.localize(dt, is_dst=False).astimezone(dst_tz)
        df['time_ist'] = df['time'].apply(convert_tz)
        
    df = df.dropna(subset=['time_ist']).reset_index(drop=True)
    logger.info(f"Loaded {len(df)} candles.")
    return df

def run_backtest(df, config):
    trades = []
    equity = config['initial_capital']
    
    # -- Date Filtering --
    if config['duration_months'] > 0:
        last_date = df['time_ist'].iloc[-1]
        start_cutoff = last_date - pd.DateOffset(months=config['duration_months'])
        
        # Check if cutoff is before actual start
        if start_cutoff < df['time_ist'].iloc[0]:
            print(f"Warning: Requested {config['duration_months']} months exceeds data availability. Using all data.")
        else:
            df = df[df['time_ist'] >= start_cutoff].reset_index(drop=True)
            
    print(f"\nBacktesting Range: {df['time_ist'].iloc[0]} to {df['time_ist'].iloc[-1]}")
    print(f"Total Candles: {len(df)}")
    
    equity_curve = [{'time': df['time_ist'].iloc[0], 'equity': equity}]
    
    # Unpack Config
    ASIAN_START = time(3, 30)
    ASIAN_END = time(13, 30)
    TRADE_END = time(21, 30)
    
    SL_PIPS = config['sl_pips']
    TP_PIPS = config['tp_pips']
    PIP_VAL_PRICE = 0.10 # 1 Pip = 0.10 Price
    
    # State
    in_position = False
    position = None 
    asian_high = -1.0
    asian_low = 1000000.0
    range_set = False
    
    # Pre-computation
    time_col = df['time_ist'].dt.time
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    times = df['time_ist'].values
    
    logger.info(f"Running simulation with {config['mode']} sizing...")
    
    for i in range(len(df)):
        t = time_col[i]
        curr_high = highs[i]
        curr_low = lows[i]
        curr_close = closes[i]
        curr_time = times[i]
        
        # 1. Manage Existing Position
        if in_position:
            p = position
            exit_price = None
            exit_reason = ""
            
            p['duration'] += 15 # Add 15 mins
            
            # Check SL/TP
            if p['type'] == 'long':
                if curr_low <= p['sl']:
                    exit_price = p['sl']
                    exit_reason = "SL"
                elif curr_high >= p['tp']:
                    exit_price = p['tp']
                    exit_reason = "TP"
                elif t >= TRADE_END:
                    exit_price = curr_close
                    exit_reason = "Session Close"
                
                # Trailing
                if not exit_price:
                    # Logic: If price moves favorably by Trigger, Trail by Dist
                    # "trail_points = 20 * 10" -> 20 Pips trigger
                    trigger_price = p['entry_price'] + (config['trail_trigger'] * PIP_VAL_PRICE)
                    if curr_high >= trigger_price:
                        # Trail to High - TrailDist
                        # "trail_offset = 5 * 10" -> 5 Pips distance
                        new_sl = curr_high - (config['trail_dist'] * PIP_VAL_PRICE)
                        if new_sl > p['sl']:
                            p['sl'] = new_sl
                            
            else: # Short
                if curr_high >= p['sl']:
                    exit_price = p['sl']
                    exit_reason = "SL"
                elif curr_low <= p['tp']:
                    exit_price = p['tp']
                    exit_reason = "TP"
                elif t >= TRADE_END:
                    exit_price = curr_close
                    exit_reason = "Session Close"
                    
                # Trailing
                if not exit_price:
                    trigger_price = p['entry_price'] - (config['trail_trigger'] * PIP_VAL_PRICE)
                    if curr_low <= trigger_price:
                        new_sl = curr_low + (config['trail_dist'] * PIP_VAL_PRICE)
                        if new_sl < p['sl']:
                            p['sl'] = new_sl

            if exit_price:
                # Calculate PnL
                # Standard Lot (1.0) = $10 per pip? 
                # XAUUSD: 1 lot = 100 oz. 1 pip (0.10) move = $10.
                # Profit = (Diff / 0.10) * 10 * Lots = Diff * 100 * Lots?
                # Wait. Price Diff $1.00 = 10 Pips. 
                # 1 Lot ($1 move) = $100 Profit.
                # So PnL = PriceDiff * 100 * Lots.
                
                price_diff = (exit_price - p['entry_price']) if p['type'] == 'long' else (p['entry_price'] - exit_price)
                pnl = price_diff * 100.0 * p['size']
                
                equity += pnl
                trades.append({
                    'entry_time': p['entry_time_val'],
                    'exit_time': curr_time,
                    'type': p['type'],
                    'entry_price': p['entry_price'],
                    'exit_price': exit_price,
                    'size': p['size'],
                    'pnl': pnl,
                    'reason': exit_reason,
                    'equity_after': equity
                })
                in_position = False
                position = None
        
        # 2. Session Logic
        is_asian = (t >= ASIAN_START) and (t < ASIAN_END)
        is_trade = (t >= ASIAN_END) and (t < TRADE_END)
        
        if t == ASIAN_START:
            asian_high = curr_high
            asian_low = curr_low
            range_set = True
        elif is_asian:
            asian_high = max(asian_high, curr_high)
            asian_low = min(asian_low, curr_low)
            
        # 3. Entry Logic
        if is_trade and not in_position and range_set:
            sl_dist_price = SL_PIPS * PIP_VAL_PRICE
            tp_dist_price = TP_PIPS * PIP_VAL_PRICE
            entry_signal = None
            
            if curr_close > asian_high:
                entry_signal = 'long'
                sl_price = asian_high - sl_dist_price # Asian Low or fixed distance? User said "Stop Loss (Pips)"
                # "use stoploss in SL instead of points" -> implies fixed distance SL.
                # Let's use Entry - SL_Pips.
                entry_price = curr_close
                sl_price = entry_price - sl_dist_price
                tp_price = entry_price + tp_dist_price
                
            elif curr_close < asian_low:
                entry_signal = 'short'
                entry_price = curr_close
                sl_price = entry_price + sl_dist_price
                tp_price = entry_price - tp_dist_price
                
            if entry_signal:
                # Sizing
                lots = 0.0
                if config['mode'] == 'fixed':
                    lots = config['fixed_lots']
                else:
                    risk_amt = equity * config['risk_pct']
                    # Risk = SL_Distance * 100 * Lots
                    # Lots = Risk / (SL_Dist * 100)
                    sl_dist = abs(entry_price - sl_price)
                    if sl_dist == 0: sl_dist = 0.1
                    lots = risk_amt / (sl_dist * 100.0)
                    lots = round(lots, 2)
                    if lots < 0.01: lots = 0.01

                position = {
                    'type': entry_signal,
                    'entry_time_val': curr_time,
                    'entry_price': entry_price,
                    'sl': sl_price,
                    'tp': tp_price,
                    'size': lots,
                    'duration': 0
                }
                in_position = True
        
        # Reset Range at end of session
        if t >= TRADE_END:
            range_set = False
            
        # Record Equity (Daily or Candle?) 
        # For curve, candle is fine, but maybe too dense. Let's record daily closes? 
        # Or just use the trade exit points for the curve.
        # Let's record hourly equity?
        # For now, we reconstruct curve from trades.
        pass

    return pd.DataFrame(trades), equity

def generate_report(trades_df, initial_equity, final_equity):
    if trades_df.empty:
        print("No trades generated.")
        return

    # Metrics
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = (n_wins / total_trades) * 100
    
    gross_profit = wins['pnl'].sum() if n_wins > 0 else 0.0
    gross_loss = abs(losses['pnl'].sum()) if n_losses > 0 else 0.0
    net_profit = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
    
    avg_win = wins['pnl'].mean() if n_wins > 0 else 0.0
    avg_loss = losses['pnl'].mean() if n_losses > 0 else 0.0
    
    # Drawdown
    # Reconstruct equity curve
    trades_df['cum_pnl'] = trades_df['pnl'].cumsum()
    trades_df['equity'] = initial_equity + trades_df['cum_pnl']
    
    peak = trades_df['equity'].cummax()
    drawdown = trades_df['equity'] - peak
    drawdown_pct = (drawdown / peak) * 100
    max_dd_abs = drawdown.min()
    max_dd_pct = drawdown_pct.min()
    
    # Daily Stats
    trades_df['date'] = pd.to_datetime(trades_df['exit_time']).dt.date
    daily_counts = trades_df.groupby('date').size()
    avg_trades_daily = daily_counts.mean()
    
    # Sharpe (approx)
    # returns = trades_df['pnl'] / initial_equity
    # sharpe = np.sqrt(252) * returns.mean() / returns.std() # Very rough for trade-based
    
    print("==================================================")
    print("             BACKTEST PERFORMANCE REPORT          ")
    print("==================================================")
    print(f"Initial Deposit:     ${initial_equity:,.2f}")
    print(f"Final Balance:       ${final_equity:,.2f}")
    print(f"Net Profit:          ${net_profit:,.2f} ({(net_profit/initial_equity)*100:.2f}%)")
    print("-" * 50)
    print(f"Total Trades:        {total_trades}")
    print(f"Win Rate:            {win_rate:.2f}% ({n_wins} W / {n_losses} L)")
    print(f"Profit Factor:       {profit_factor:.2f}")
    print(f"Avg Win:             ${avg_win:,.2f}")
    print(f"Avg Loss:            ${avg_loss:,.2f}")
    print("-" * 50)
    print(f"Max Drawdown:        ${max_dd_abs:,.2f} ({max_dd_pct:.2f}%)")
    print(f"Gross Profit:        ${gross_profit:,.2f}")
    print(f"Gross Loss:          ${gross_loss:,.2f}")
    print(f"Avg Trades/Day:      {avg_trades_daily:.1f}")
    print("==================================================")
    
    # Save CSVs
    trades_df.to_csv(OUTPUT_TRADES_PATH, index=False)
    equity_df = trades_df[['exit_time', 'equity']].copy()
    equity_df.to_csv(OUTPUT_EQUITY_PATH, index=False)
    
    # Plotting
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(pd.to_datetime(trades_df['exit_time']), trades_df['equity'], label='Equity')
        plt.title('Account Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Balance ($)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.savefig(OUTPUT_PLOT_PATH)
        print(f"Metrics saved to {OUTPUT_TRADES_PATH}")
        print(f"Equity curve plot saved to {OUTPUT_PLOT_PATH}")
    except Exception as e:
        print(f"Could not generate plot: {e}")

if __name__ == "__main__":
    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
    else:
        # Get Inputs
        config = get_user_inputs()
        
        # Load Data
        df = load_data(DATA_PATH)
        
        # Run
        trades, final_bal = run_backtest(df, config)
        
        # Report
        generate_report(trades, config['initial_capital'], final_bal)
