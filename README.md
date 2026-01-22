# Gold Breakout AlgoTrader

Welcome to the **Gold Breakout AlgoTrader**! This tool is designed to help you automate or backtest trading strategies on Gold (XAUUSD), specifically focusing on session-based breakout logic (Asian Session High/Low).

We have designed this to be easy to use, even if you are not a programmer.

## 🚀 Key Features

*   **Simple Dashboard**: A web-based interface to change settings and see results without touching code.
*   **Timezone Smart**: You can input times in your local time (e.g., IST), and the system automatically converts them to your Broker's time (e.g., Athens/EET).
*   **Resume Capability**: If your computer restarts or the script stops, it remembers your trades and positions so you can resume smoothly.
*   **Organized Results**: Every time you run a test, a new folder is created with charts, trade logs, and performance metrics.

---

## 🛠️ Installation (First Time Only)

Before you start, you need to set up the environment.

1.  **Open Terminal**: Open your command prompt or terminal in this project folder.
2.  **Create a Virtual Environment** (Optional but recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    Run this command to install all necessary tools:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ How to Use (The Easy Way)

The easiest way to use this tool is through our **Dashboard**.

1.  **Start the Dashboard**:
    Run this command in your terminal:
    ```bash
    streamlit run dashboard/app.py
    ```
2.  **Open Browser**: A new tab should open in your default web browser (usually at `http://localhost:8501`).

### Dashboard Tabs

*   **Configuration**:
    *   Here you can change settings like `RISK_PERCENTAGE`, `Lot Size`, or `Trading Times`.
    *   **Timezones**: make sure `USER` is set to your timezone (e.g., `Asia/Kolkata`) and `BROKER` to your broker's (e.g., `Europe/Athens`).
    *   Click **"Save Config"** to apply changes.

*   **Backtest Results**:
    *   Select a past run from the dropdown.
    *   View your Profit/Loss, Win Rate, and a list of all trades taken.

*   **Live Monitor**:
    *   Check the current status of the running strategy.
    *   See open positions and current Account Equity.

---

## 📂 Understanding Results

All your run data is saved in the `results` folder.
*   Each run gets its own folder like: `results/2025-01-22_15-30-StrategyName/`
*   Inside you will find:
    *   `trades.csv`: A spreadsheet of every trade.
    *   `performance.json`: A summary of your wins, losses, and profit.
    *   `run.log`: Technical logs for debugging.

---

## ❓ Common Questions

**Q: My broker is in a different timezone different from Athens?**
A: Go to the Dashboard -> Configuration and change the `BROKER` timezone under `TIMEZONE`.

**Q: How do I stop the trading?**
A: Press `Ctrl+C` in the terminal where the script is running.

**Q: Can I run this on a server?**
A: Yes! Just follow the installation steps on your VPS or cloud server.
