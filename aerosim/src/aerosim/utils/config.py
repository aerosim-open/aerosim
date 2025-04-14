import json
from pathlib import Path
from typing import Dict, Any

class Config:
    """Configuration management class for Aerosim Utils."""
    
    DEFAULT_CONFIG: Dict[str, Any] = {
        # Directory paths
        "DEFAULT_INPUT_DIR": "inputs",
        "DEFAULT_OUTPUT_DIR": "outputs",
        "DEFAULT_TRACKS_DIR": "tracks",
        "DEFAULT_TRAJECTORIES_DIR": "trajectories",
        "DEFAULT_VISUALIZATION_DIR": "visualization",
        "DEFAULT_FOLIUM_DIR": "visualization/folium",
        "DEFAULT_REPORTS_DIR": "reports",
        
        # Default coordinates and parameters
        "DEFAULT_CENTER_LAT": 34.217411,
        "DEFAULT_CENTER_LON": -118.491081,
        "DEFAULT_RADIUS_KM": 50.0,
        "DEFAULT_ALTITUDE": 1000.0,
        "DEFAULT_INTERVAL_SECONDS": 5.0,
        
        # Scenario generation
        "DEFAULT_SCENARIO_NAME": "auto_gen_scenario",
        "DEFAULT_WORLD_NAME": "default_world",
        
        # Visualization settings
        "DEFAULT_VISUALIZATION_METHOD": "folium",  # or 'kml'
        "DEFAULT_MAP_CENTER": [34.217411, -118.491081],
        "DEFAULT_MAP_ZOOM": 12,
        "DEFAULT_TRACK_COLORS": ["red", "blue", "green", "purple", "orange"],
        
        # Reporting settings
        "DEFAULT_REPORT_FORMAT": "markdown",  # or 'html'
        "DEFAULT_PLOT_FORMAT": "png",  # or 'svg', 'pdf'
        "DEFAULT_PLOT_SIZE": [12, 8],  # width, height in inches
        
        # Sensor configuration
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
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate the current configuration."""
        try:
            # Validate paths
            for key in cls._config:
                if key.endswith("_DIR"):
                    path = Path(cls._config[key])
                    if not path.is_absolute():
                        # Convert to absolute path relative to package root
                        cls._config[key] = str(Path(__file__).parent.parent / path)
            
            # Validate numeric values
            assert isinstance(cls._config["DEFAULT_CENTER_LAT"], (int, float))
            assert isinstance(cls._config["DEFAULT_CENTER_LON"], (int, float))
            assert isinstance(cls._config["DEFAULT_RADIUS_KM"], (int, float))
            assert isinstance(cls._config["DEFAULT_ALTITUDE"], (int, float))
            assert isinstance(cls._config["DEFAULT_INTERVAL_SECONDS"], (int, float))
            
            # Validate visualization settings
            assert cls._config["DEFAULT_VISUALIZATION_METHOD"] in ["folium", "kml"]
            assert len(cls._config["DEFAULT_MAP_CENTER"]) == 2
            assert isinstance(cls._config["DEFAULT_MAP_ZOOM"], int)
            assert isinstance(cls._config["DEFAULT_TRACK_COLORS"], list)
            
            # Validate reporting settings
            assert cls._config["DEFAULT_REPORT_FORMAT"] in ["markdown", "html"]
            assert cls._config["DEFAULT_PLOT_FORMAT"] in ["png", "svg", "pdf"]
            assert len(cls._config["DEFAULT_PLOT_SIZE"]) == 2
            
            return True
        except (AssertionError, KeyError) as e:
            print(f"Configuration validation failed: {str(e)}")
            return False
