import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from src.production.config import config

logger = logging.getLogger(__name__)

class ResultManager:
    def __init__(self, strategy_name="Strategy"):
        self.base_dir = Path(config.get("PATHS", {}).get("RESULTS_DIR", "results"))
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.run_dir = self.base_dir / f"{self.timestamp}-{strategy_name}"
        
        self.ensure_dir()
        self.setup_logging()

    def ensure_dir(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        log_file = self.run_dir / "run.log"
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add to root logger
        logging.getLogger().addHandler(file_handler)
        logger.info(f"Logging initialized in {self.run_dir}")

    def save_trades(self, trades_list):
        if not trades_list:
            return
            
        csv_path = self.run_dir / "trades.csv"
        keys = trades_list[0].keys()
        
        try:
            with open(csv_path, 'w', newline='') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(trades_list)
            logger.info(f"Trades saved to {csv_path}")
        except Exception as e:
            logger.error(f"Failed to save trades: {e}")

    def save_performance(self, metrics_dict):
        json_path = self.run_dir / "performance.json"
        try:
            with open(json_path, 'w') as f:
                json.dump(metrics_dict, f, indent=4)
            logger.info(f"Performance metrics saved to {json_path}")
        except Exception as e:
            logger.error(f"Failed to save performance: {e}")

    def get_run_dir(self):
        return self.run_dir
