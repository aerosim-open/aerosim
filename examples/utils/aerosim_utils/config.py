import json
from pathlib import Path
from typing import Dict, Any

class Config:
    """Configuration management class for Aerosim Utils."""
    
    DEFAULT_CONFIG: Dict[str, Any] = {
        "DEFAULT_INPUT_DIR": "inputs",
        "DEFAULT_OUTPUT_DIR": "outputs",
        "DEFAULT_TRACKS_DIR": "tracks",
        "DEFAULT_TRAJECTORIES_DIR": "trajectories",
        "DEFAULT_CENTER_LAT": 34.217411,
        "DEFAULT_CENTER_LON": -118.491081,
        "DEFAULT_RADIUS_KM": 50.0,
        "DEFAULT_ALTITUDE": 1000.0,
        "DEFAULT_INTERVAL_SECONDS": 5.0,
        "DEFAULT_SCENARIO_NAME": "auto_gen_scenario",
        "DEFAULT_WORLD_NAME": "default_world",
        "DEFAULT_SENSOR_CONFIG": {
            "type": "camera",
            "fov": 90,
            "resolution": [1920, 1080],
            "update_rate": 30
        }
    }
    
    _instance = None
    _config: Dict[str, Any] = DEFAULT_CONFIG.copy()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return cls._config.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a configuration value."""
        cls._config[key] = value
    
    @classmethod
    def save_config(cls, config_file: str) -> None:
        """Save current configuration to file."""
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(cls._config, f, indent=4)
    
    @classmethod
    def load_config(cls, config_file: str) -> None:
        """Load configuration from file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            loaded_config = json.load(f)
            cls._config.update(loaded_config)
    
    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults."""
        cls._config = cls.DEFAULT_CONFIG.copy()
