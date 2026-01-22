import yaml
import pytz
from datetime import datetime, time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path="config.yaml"):
        # Look for config in root
        root_path = Path(__file__).parent.parent.parent
        self.config_path = root_path / config_path
        
        if not self.config_path.exists():
            # Fallback to current dir if not found in root (test compatibility)
            self.config_path = Path(config_path)

        self.data = self._load_config()
        self._setup_timezones()

    def _load_config(self):
        if not self.config_path.exists():
            # Try to load json if yaml missing (migration support)
            json_path = self.config_path.with_suffix('.json')
            if json_path.exists():
                 import json
                 with open(json_path, 'r') as f:
                     return json.load(f)
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _setup_timezones(self):
        tz_conf = self.get("TIMEZONE", {})
        self.broker_tz_name = tz_conf.get("BROKER", "Europe/Athens")
        self.user_tz_name = tz_conf.get("USER", "Asia/Kolkata")
        
        try:
            self.broker_tz = pytz.timezone(self.broker_tz_name)
            self.user_tz = pytz.timezone(self.user_tz_name)
        except pytz.UnknownTimeZoneError as e:
            logger.error(f"Invalid timezone: {e}")
            self.broker_tz = pytz.utc
            self.user_tz = pytz.utc

    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value

    def reload(self):
        self.data = self._load_config()
        self._setup_timezones()

    # Timezone Helpers
    def convert_to_broker_time(self, user_time_obj):
        """Convert a user-time (time or datetime) to broker-time."""
        # This is tricky for just 'time' objects because date matters for DST
        # We assume 'today' for date if only time is passed, or user can pass datetime
        
        if isinstance(user_time_obj, time):
            dt = datetime.now(self.user_tz).replace(
                hour=user_time_obj.hour, 
                minute=user_time_obj.minute, 
                second=user_time_obj.second, 
                microsecond=0
            )
        elif isinstance(user_time_obj, datetime):
            dt = user_time_obj
            if dt.tzinfo is None:
                dt = self.user_tz.localize(dt)
        else:
            return user_time_obj

        broker_dt = dt.astimezone(self.broker_tz)
        
        if isinstance(user_time_obj, time):
            return broker_dt.time()
        return broker_dt

# Global config instance
try:
    config = Config()
except Exception as e:
    config = None
    print(f"Warning: Config initialization failed: {e}")
