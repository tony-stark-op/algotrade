import sys
from pathlib import Path
from datetime import time, datetime
import pytz

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.production.config import config
from src.strategies.gold_breakout import GoldBreakout
from src.utils.results import ResultManager

def test_config_loading():
    print("Testing Config Loading...")
    assert config is not None
    assert config.get("TIMEZONE", {}).get("BROKER") == "Europe/Athens"
    print("PASS: Config loaded.")

def test_timezone_conversion():
    print("Testing Timezone Conversion...")
    # IST 03:30 -> Athens ??
    # Today
    ist = pytz.timezone("Asia/Kolkata")
    athens = pytz.timezone("Europe/Athens")
    
    t_ist = time(3, 30)
    t_athens = config.convert_to_broker_time(t_ist)
    
    # Verify manually
    now = datetime.now()
    dt_ist = ist.localize(datetime.combine(now.date(), t_ist))
    dt_athens = dt_ist.astimezone(athens)
    
    print(f"IST: {t_ist} -> Athens: {t_athens}")
    assert t_athens.hour == dt_athens.time().hour
    assert t_athens.minute == dt_athens.time().minute
    print("PASS: Timezone conversion matches.")

def test_strategy_init():
    print("Testing Strategy Initialization...")
    strat = GoldBreakout(config)
    strat.on_init()
    
    print(f"Strategy Asian Start (Broker Time): {strat.asian_start}")
    print(f"Strategy Asian End (Broker Time): {strat.asian_end}")
    
    # Check if times are converted
    assert strat.asian_start != time(3, 30) # Should be different unless coincidentally same offset
    print("PASS: Strategy initialized with converted times.")

def test_result_manager():
    print("Testing ResultManager...")
    rm = ResultManager("TestRun")
    path = rm.get_run_dir()
    print(f"Created run dir: {path}")
    assert path.exists()
    assert (path / "run.log").exists()
    print("PASS: ResultManager created format.")

if __name__ == "__main__":
    try:
        test_config_loading()
        test_timezone_conversion()
        test_strategy_init()
        test_result_manager()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
