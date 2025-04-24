"""Configuration management for Minecraft Command & Control."""

import json
from pathlib import Path
from typing import Dict, Any


class Config:
    def __init__(self):
        self.config_file = Path("config.json")
        self.default_config = {
            "server": {
                "tmux_session": "minecraft",
                "command_delay": 0.1,  # delay in seconds between commands
            },
            "history_size": 1000,
        }
        self.current_config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.current_config = json.load(f)
        else:
            self.current_config = self.default_config.copy()
            self.save()
        return self.current_config

    def save(self):
        """Save current configuration to file."""
        with open(self.config_file, "w") as f:
            json.dump(self.current_config, f, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.current_config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value and save."""
        self.current_config[key] = value
        self.save()
