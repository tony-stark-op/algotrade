import json
from pathlib import Path

class Config:
    def __init__(self, config_path="config.json"):
        self.config_path = Path(config_path)
        self.data = self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def reload(self):
        self.data = self._load_config()

# Global config instance for easy access
try:
    config = Config()
except FileNotFoundError:
    config = None 
    print("Warning: config.json not found at initialization.")
