import pandas as pd
import pytz
from datetime import datetime
from abc import ABC, abstractmethod
import logging
from pathlib import Path
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from src.config import config

# Logging
logger = logging.getLogger(__name__)

class DataLoader(ABC):
    @abstractmethod
    def fetch_data(self, symbol, timeframe_str, start_dt, end_dt):
        pass

class MT5Loader(DataLoader):
    def __init__(self):
        self._connected = False

    def initialize(self):
        if not mt5:
            logger.error("MetaTrader5 package not found.")
            return False
            
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed, error code: {mt5.last_error()}")
            return False
        
        self._connected = True
        logger.info("MT5 Initialized successfully.")
        return True

    def shutdown(self):
        if self._connected and mt5:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 connection closed.")

    def fetch_data(self, symbol, timeframe_str, start_dt, end_dt):
        if not self._connected:
            if not self.initialize():
                 raise ConnectionError("Could not connect to MT5")

        # Map timeframe string to MT5 constant
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        tf = tf_map.get(timeframe_str)
        if not tf:
             raise ValueError(f"Unsupported timeframe: {timeframe_str}")

        # Ensure datetimes are timezone-aware or handle accordingly
        # MT5 usually expects UTC or server time. Let's assume standard datetime objects.
        rates = mt5.copy_rates_range(symbol, tf, start_dt, end_dt)
        
        if rates is None or len(rates) == 0:
            logger.warning("No data received from MT5")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Rename columns to standard
        # MT5 returns: time, open, high, low, close, tick_volume, spread, real_volume
        df.rename(columns={'tick_volume': 'vol'}, inplace=True)
        
        return df[['time', 'open', 'high', 'low', 'close', 'vol']]

class CSVLoader(DataLoader):
    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def fetch_data(self, symbol, timeframe_str, start_dt, end_dt):
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV Data file not found: {self.file_path}")

        logger.info(f"Loading data from CSV: {self.file_path}")
        # Assuming flexible CSV reading, but optimized for the user's previous format
        # Format from original run_gold_breakout.py: tab-separated, no header? 
        # Or maybe standard CSV. Let's try to detect or support the format from original script.
        # Original: sep='\t', names=["time_str", "open", "high", "low", "close", "vol"]
        
        try:
            # Try reading as tab separated first (legacy support)
            df = pd.read_csv(self.file_path, sep='\t', header=None, 
                             names=["time_str", "open", "high", "low", "close", "vol"])
            if df.shape[1] == 1: # Failed to parse tabs correctly, maybe it is comma
                 df = pd.read_csv(self.file_path) # Auto-detect
        except Exception:
             # Fallback to standard read
             df = pd.read_csv(self.file_path)

        # Standardize columns
        df.columns = [c.lower() for c in df.columns]
        
        # Handle Time
        if 'time_str' in df.columns:
            df['time'] = pd.to_datetime(df['time_str'])
        elif 'date' in df.columns:
            df['time'] = pd.to_datetime(df['date'])
        elif 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            
        # Filter range
        if start_dt:
             df = df[df['time'] >= pd.to_datetime(start_dt)]
        if end_dt:
             df = df[df['time'] <= pd.to_datetime(end_dt)]
             
        df = df.sort_values('time').reset_index(drop=True)
        
        # Ensure required columns
        req_cols = ['time', 'open', 'high', 'low', 'close']
        for c in req_cols:
            if c not in df.columns:
                raise ValueError(f"CSV missing required column: {c}")
                
        # Optional vol
        if 'vol' not in df.columns:
            df['vol'] = 0
            
        return df[req_cols + ['vol']]

def get_data_loader():
    method = config.get("DATALOADING", "LIVE")
    if method in ["LIVE", "HISTORY"]:
        return MT5Loader()
    elif method == "CUSTOM":
        path = config.get("DATA_FILE_PATH")
        return CSVLoader(path)
    else:
        raise ValueError(f"Unknown DATALOADING method: {method}")
