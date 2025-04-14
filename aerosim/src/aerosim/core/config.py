"""
Configuration handling for AeroSim.

This module provides utilities for loading, validating, and managing simulation configurations.
"""

import os
import json
from typing import Dict, Any, Optional, List


class SimConfig:
    """
    Simulation configuration handler.
    
    This class provides utilities for loading, validating, and managing simulation configurations.
    """
    
    def __init__(self, config_file: Optional[str] = None, config_dir: str = os.getcwd()) -> None:
        """
        Initialize the simulation configuration.
        
        Args:
            config_file: Path to the simulation configuration file
            config_dir: Directory containing the simulation configuration file
        """
        self.config_dir = config_dir
        self.config_json = None
        
        if config_file:
            self.load(config_file)
    
    def load(self, config_file: str) -> Dict[str, Any]:
        """
        Load a simulation configuration from a file.
        
        Args:
            config_file: Path to the simulation configuration file
            
        Returns:
            The loaded configuration as a dictionary
        """
        config_path = os.path.abspath(os.path.join(self.config_dir, config_file))
        print(f"Loading simulation configuration from {config_path}...")
        
        with open(config_path, "r") as file:
            self.config_json = json.load(file)
        
        return self.config_json
    
    def save(self, config_file: str) -> None:
        """
        Save the current simulation configuration to a file.
        
        Args:
            config_file: Path to save the simulation configuration
        """
        if not self.config_json:
            raise ValueError("No configuration loaded to save")
        
        config_path = os.path.abspath(os.path.join(self.config_dir, config_file))
        print(f"Saving simulation configuration to {config_path}...")
        
        with open(config_path, "w") as file:
            json.dump(self.config_json, file, indent=4)
    
    def get_fmu_models(self) -> List[Dict[str, Any]]:
        """
        Get the FMU models from the configuration.
        
        Returns:
            List of FMU model configurations
        """
        if not self.config_json:
            raise ValueError("No configuration loaded")
        
        return self.config_json.get("fmu_models", [])
    
    def get_world_config(self) -> Dict[str, Any]:
        """
        Get the world configuration.
        
        Returns:
            World configuration dictionary
        """
        if not self.config_json:
            raise ValueError("No configuration loaded")
        
        return self.config_json.get("world", {})
    
    def update_world_origin(self, latitude: float, longitude: float, altitude: float) -> None:
        """
        Update the world origin in the configuration.
        
        Args:
            latitude: Origin latitude in degrees
            longitude: Origin longitude in degrees
            altitude: Origin altitude in meters
        """
        if not self.config_json:
            raise ValueError("No configuration loaded")
        
        if "world" not in self.config_json:
            self.config_json["world"] = {}
        
        if "origin" not in self.config_json["world"]:
            self.config_json["world"]["origin"] = {}
        
        self.config_json["world"]["origin"]["latitude"] = latitude
        self.config_json["world"]["origin"]["longitude"] = longitude
        self.config_json["world"]["origin"]["altitude"] = altitude
