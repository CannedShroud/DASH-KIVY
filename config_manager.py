import json
import os
from enum import Enum

class ConfigManager:
    CONFIG_FILE = "config.json"
    
    # Defaults mirroring the original wifi.py hardcoded values
    DEFAULT_CONFIG = {
        "gauges": ["BOOST", "IAT", "STFT", "COOLANT_TEMP", "OIL_TEMP", "VOLTAGE"],
        "datacells": ["BOOST", "IAT", "STFT", "COOLANT_TEMP", "OIL_TEMP", "VOLTAGE"],
        "redline": 6000,
        "warnings": ["WARMUP_STATUS", "BATTERY_STATUS"],
        "fast_pids": ["RPM", "BOOST", "TIMING", "THROTTLE", "STFT"],
        "slow_pids": ["IAT", "COOLANT_TEMP", "OIL_TEMP", "LTFT", "VOLTAGE", "LOAD", "AFR"]
    }

    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Error loading config, using defaults.")
            return self.DEFAULT_CONFIG

    def save_config(self, config=None):
        if config:
            self.config = config
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

config_manager = ConfigManager()
