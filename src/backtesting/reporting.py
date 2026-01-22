import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def generate_report(trades_df, equity_df, initial_equity, output_dir="."):
    if trades_df.empty:
        print("No trades generated.")
        return

    # Metrics
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = (n_wins / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = wins['pnl'].sum() if n_wins > 0 else 0.0
    gross_loss = abs(losses['pnl'].sum()) if n_losses > 0 else 0.0
    net_profit = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
    
    avg_win = wins['pnl'].mean() if n_wins > 0 else 0.0
    avg_loss = losses['pnl'].mean() if n_losses > 0 else 0.0
    
    # Drawdown
    equity_series = equity_df['equity']
    peak = equity_series.cummax()
    drawdown = equity_series - peak
    drawdown_pct = (drawdown / peak) * 100
    
    max_dd_abs = drawdown.min()
    max_dd_pct = drawdown_pct.min()
    
    final_balance = equity_series.iloc[-1]
    
    # Advanced Metrics (SQN, Payoff)
    # SQN = sqrt(N) * (Avg PnL / Std Dev PnL)
    pnls = trades_df['pnl']
    avg_pnl = pnls.mean()
    std_pnl = pnls.std()
    sqn = (np.sqrt(total_trades) * (avg_pnl / std_pnl)) if std_pnl > 0 else 0
    
    # Text Report
    report = []
    report.append("==================================================")
    report.append("             BACKTEST PERFORMANCE REPORT          ")
    report.append("==================================================")
    report.append(f"Initial Deposit:     ${initial_equity:,.2f}")
    report.append(f"Final Balance:       ${final_balance:,.2f}")
    report.append(f"Net Profit:          ${net_profit:,.2f} ({(net_profit/initial_equity)*100:.2f}%)")
    report.append("-" * 50)
    report.append(f"Total Trades:        {total_trades}")
    report.append(f"Win Rate:            {win_rate:.2f}% ({n_wins} W / {n_losses} L)")
    report.append(f"Profit Factor:       {profit_factor:.2f}")
    report.append(f"SQN:                 {sqn:.2f}")
    report.append(f"Avg Win:             ${avg_win:,.2f}")
    report.append(f"Avg Loss:            ${avg_loss:,.2f}")
    report.append("-" * 50)
    report.append(f"Max Drawdown:        ${max_dd_abs:,.2f} ({max_dd_pct:.2f}%)")
    report.append("==================================================")
    
    print("\n".join(report))
    
    # Save to File
    out_path = Path(output_dir)
    with open(out_path / "report.txt", "w") as f:
        f.write("\n".join(report))
        
    trades_df.to_csv(out_path / "trades.csv", index=False)
    
    # Plotting
    try:
        plt.figure(figsize=(12, 8))
        
        # Subplot 1: Equity Curve
        plt.subplot(2, 1, 1)
        plt.plot(pd.to_datetime(equity_df['time']), equity_df['equity'], label='Equity', color='blue')
        plt.title('Equity Curve')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Subplot 2: Drawdown
        plt.subplot(2, 1, 2)
        plt.fill_between(pd.to_datetime(equity_df['time']), drawdown_pct, 0, color='red', alpha=0.3, label='Drawdown %')
        plt.title('Drawdown %')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(out_path / "equity_curve.png")
        print(f"Plots saved to {out_path / 'equity_curve.png'}")
    except Exception as e:
        print(f"Plotting failed: {e}")
