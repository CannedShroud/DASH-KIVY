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
        "slow_pids": ["IAT", "COOLANT_TEMP", "OIL_TEMP", "LTFT", "VOLTAGE", "LOAD", "AFR"],
        "show_rpm_bar": True
    }

    def __init__(self):
        self.last_mtime = 0
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
        
        try:
            self.last_mtime = os.path.getmtime(self.CONFIG_FILE)
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Error loading config, using defaults.")
            return self.DEFAULT_CONFIG

    def check_for_changes(self):
        """Returns True if the config file has changed on disk."""
        try:
            if not os.path.exists(self.CONFIG_FILE):
                return False
            
            current_mtime = os.path.getmtime(self.CONFIG_FILE)
            if current_mtime > self.last_mtime:
                print(f"[*] Config change detected! Reloading {self.CONFIG_FILE}...")
                self.load_config_into_memory()
                return True
        except OSError:
            pass
        return False

    def load_config_into_memory(self):
        """Reloads config from disk and updates internal state."""
        self.config = self.load_config()

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
