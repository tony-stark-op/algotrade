import streamlit as st
import yaml
import json
import pandas as pd
import pandas as pd
from pathlib import Path
import sys
import subprocess
from datetime import time

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Gold Breakout Trader",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

CONFIG_PATH = Path("config.yaml")

# --- Styles ---
st.markdown("""
<style>
    .main_header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFD700; /* Gold */
        text-align: center;
        margin-bottom: 2rem;
    }
    .section_header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #E0E0E0;
        border-bottom: 2px solid #333;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .stButton>button {
        background-color: #FFD700;
        color: black;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

def save_config(new_config):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(new_config, f, default_flow_style=False)

def run_script(script_path):
    """Run a python script and capture output."""
    try:
        # Use sys.executable to ensure we use the same python env (e.g. venv)
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent 
        )
        return result
    except Exception as e:
        return str(e)

def main():
    st.markdown('<div class="main_header">👑 Gold Breakout AlgoTrader</div>', unsafe_allow_html=True)
    
    config_data = load_config()
    
    # Sidebar Navigation
    page = st.sidebar.radio("Navigation", ["⚙️ Configuration", "📊 Backtest Results", "🔴 Live Monitor"])
    
    # ---------------------------------------------------------
    # PAGE 1: CONFIGURATION
    # ---------------------------------------------------------
    if page == "⚙️ Configuration":
        st.write("### 🛠️ System Settings")
        st.info("Adjust your trading parameters here. Changes are saved to `config.yaml`.")

        with st.form("config_form"):
            # --- General Settings ---
            st.markdown('<div class="section_header">1. General</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                mode_opts = ["BACKTESTING", "LIVE"]
                curr_mode = config_data.get("MODE", "BACKTESTING")
                mode = st.selectbox("Trading Mode", mode_opts, index=mode_opts.index(curr_mode) if curr_mode in mode_opts else 0)
            
            with col2:
                tf_opts = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
                curr_tf = config_data.get("TIMEFRAME", "M15")
                timeframe = st.selectbox("Timeframe", tf_opts, index=tf_opts.index(curr_tf) if curr_tf in tf_opts else 2)
                
            with col3:
                dl_opts = ["CUSTOM", "LIVE", "HISTORY"]
                curr_dl = config_data.get("DATALOADING", "CUSTOM")
                data_loading = st.selectbox("Data Source", dl_opts, index=dl_opts.index(curr_dl) if curr_dl in dl_opts else 0)
            
            # File Upload Logic
            data_path = config_data.get("DATA_FILE_PATH", "XAUUSD15.csv")
            if data_loading == "CUSTOM":
                st.caption("Data File Selection")
                uploaded_file = st.file_uploader("Upload CSV Data (Optional - Overwrites Data File Path)", type=['csv', 'txt'])
                
                if uploaded_file is not None:
                    # Save the uploaded file
                    save_path = Path(uploaded_file.name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    data_path = str(save_path)
                    st.success(f"File saved as: {data_path}")
                
                # Show current path in text input just in case
                data_path = st.text_input("Current Data Path", data_path)
            
            # --- Financial & Risk ---
            st.markdown('<div class="section_header">2. Risk Management</div>', unsafe_allow_html=True)
            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                risk_mode = st.selectbox("Risk Type", ["DYNAMIC", "STATIC"],
                                       index=0 if config_data.get("RISK_MANAGEMENT") == "DYNAMIC" else 1)
            with r_col2:
                risk_pct = st.number_input("Risk Percentage (%)", 
                                         value=float(config_data.get("RISK_PERCENTAGE", 0.5)), 
                                         step=0.1, format="%.1f")
            with r_col3:
                fixed_lot = st.number_input("Fixed Lot Size", 
                                          value=float(config_data.get("FIXED_LOT_SIZE", 0.01)), 
                                          step=0.01, format="%.2f")

            # --- Strategy Parameters ---
            st.markdown('<div class="section_header">3. Strategy Logic</div>', unsafe_allow_html=True)
            strat_params = config_data.get("STRATEGY_PARAMS", {})
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                tp_pips = st.number_input("Take Profit (Pips)", value=int(strat_params.get("TP_PIPS", 200)))
                sl_pips = st.number_input("Stop Loss (Pips)", value=int(strat_params.get("SL_PIPS", 100)))
            with s_col2:
                trail_trig = st.number_input("Trailing Trigger (Pips)", value=int(strat_params.get("TRAIL_TRIGGER_PIPS", 20)))
                trail_dist = st.number_input("Trailing Distance (Pips)", value=int(strat_params.get("TRAIL_DIST_PIPS", 5)))

            # --- Timezones & Sessions ---
            st.markdown('<div class="section_header">4. Time & Sessions</div>', unsafe_allow_html=True)
            
            tz_config = config_data.get("TIMEZONE", {})
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                user_tz = st.text_input("Your Timezone", tz_config.get("USER", "Asia/Kolkata"))
            with t_col2:
                broker_tz = st.text_input("Broker Timezone", tz_config.get("BROKER", "Europe/Athens"))
                
            session_config = config_data.get("TRADING_SESSION", {})
            st.caption("Enter times in YOUR timezone (e.g. IST). System converts them automatically.")
            ses_col1, ses_col2, ses_col3 = st.columns(3)
            with ses_col1:
                asian_start = st.text_input("Asian Start", session_config.get("ASIAN_START", "03:30"))
            with ses_col2:
                asian_end = st.text_input("Asian End / Trade Start", session_config.get("ASIAN_END", "13:30"))
            with ses_col3:
                trade_end = st.text_input("Trade End", session_config.get("TRADE_END", "21:30"))

            # --- Save Button ---
            st.markdown("---")
            if st.form_submit_button("💾 Save Configuration", use_container_width=True):
                # Reconstruct Config
                new_conf = {
                    "TIMEFRAME": timeframe,
                    "MODE": mode,
                    "DATALOADING": data_loading,
                    "DATA_FILE_PATH": data_path,
                    "RISK_MANAGEMENT": risk_mode,
                    "RISK_PERCENTAGE": risk_pct,
                    "FIXED_LOT_SIZE": fixed_lot,
                    "TIMEZONE": {
                        "USER": user_tz,
                        "BROKER": broker_tz
                    },
                    "TRADING_SESSION": {
                        "ASIAN_START": asian_start,
                        "ASIAN_END": asian_end,
                        "TRADE_END": trade_end
                    },
                    "STRATEGY_PARAMS": {
                        "TP_PIPS": tp_pips,
                        "SL_PIPS": sl_pips,
                        "TRAIL_TRIGGER_PIPS": trail_trig,
                        "TRAIL_DIST_PIPS": trail_dist
                    },
                    "PATHS": config_data.get("PATHS", {
                        "RESULTS_DIR": "results",
                        "STATE_FILE": "trade_state.pkl",
                        "LOG_FILE": "system.log"
                    })
                }
                save_config(new_conf)
                st.success("Configuration updated successfully! 🚀")
                st.rerun()

    # ---------------------------------------------------------
    # PAGE 2: BACKTEST RESULTS
    # ---------------------------------------------------------
    elif page == "📊 Backtest Results":
        st.write("### 📈 Recent Performance")
        
        # --- Run Backtest Area ---
        with st.expander("🚀 Run New Backtest", expanded=True):
            if config_data.get("MODE") != "BACKTESTING":
                st.warning(f"⚠️ Current Mode is set to **{config_data.get('MODE')}**. Please switch to **BACKTESTING** in Configuration tab to run a backtest.")
            else:
                if st.button("▶️ Run Backtest Now", use_container_width=True):
                    with st.spinner("Running Backtest... Please wait"):
                        res = run_script("src/run_backtest.py")
                        if res.returncode == 0:
                            st.success("Backtest Completed Successfully!")
                            st.rerun() # Refresh to show new results
                        else:
                            st.error("Backtest Failed!")
                            st.code(res.stderr)
                            st.code(res.stdout)

        results_dir = Path(config_data.get("PATHS", {}).get("RESULTS_DIR", "results"))
        
        if results_dir.exists():
            runs = sorted([d for d in results_dir.iterdir() if d.is_dir()], reverse=True)
            run_names = [d.name for d in runs]
            selected_run = st.selectbox("Select Run", run_names, index=0 if run_names else None)
            
            if selected_run:
                run_path = results_dir / selected_run
                st.markdown("---")
                
                # Load Performance
                perf_file = run_path / "performance.json"
                if perf_file.exists():
                    with open(perf_file, 'r') as f:
                        metrics = json.load(f)
                    st.json(metrics)
                
                # Load Trades
                trades_file = run_path / "trades.csv"
                if trades_file.exists():
                    st.subheader("Trade Log")
                    df = pd.read_csv(trades_file)
                    st.dataframe(df, use_container_width=True)
        else:
            st.info("No results found. Run a backtest to generate data.")

    # ---------------------------------------------------------
    # PAGE 3: LIVE MONITOR
    # ---------------------------------------------------------
    elif page == "🔴 Live Monitor":
        st.write("### 📡 Live Strategy State")
        
        # Start Live Button
        if config_data.get("MODE") != "LIVE":
            st.warning("⚠️ Mode is set to BACKTESTING. Switch to LIVE in Config to handle real execution.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.button("🟢 Start Live Trading (Simulation)", use_container_width=True)
            with c2:
                st.button("🛑 Stop Trading", use_container_width=True)
        
        state_file = Path(config_data.get("PATHS", {}).get("STATE_FILE", "trade_state.pkl"))
        
        if st.button("🔄 Refresh State"):
             st.rerun()
        
        if state_file.exists():
            import pickle
            try:
                with open(state_file, 'rb') as f:
                    state = pickle.load(f)
                
                # Top Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Account Equity", f"${state.get('equity', 0):,.2f}")
                m1.metric("Open Position", str(state.get('position', 'None')))
                m3.metric("Orders Pending", len(state.get('orders', [])))
                
                st.divider()
                
                # Detailed State
                with st.expander("Session Details (Asian Range)", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Asian High", state.get('asian_high', 'N/A'))
                    c2.metric("Asian Low", state.get('asian_low', 'N/A'))
                    c3.metric("Range Set?", "Yes" if state.get('range_set') else "No")
                
            except Exception as e:
                st.error(f"Could not load state: {e}")
        else:
            st.info("No active state file found.")

if __name__ == "__main__":
    main()
