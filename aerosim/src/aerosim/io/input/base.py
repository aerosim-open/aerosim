"""
Base input handler for AeroSim.

This module provides the base class for handling input from various sources.
"""

from typing import Callable, Optional


class InputHandler:
    """
    Base class for handling input from various sources.
    
    This class provides a common interface for processing input commands
    from different sources like keyboard, gamepad, or remote connections.
    """
    
    def __init__(self, command_callback: Optional[Callable] = None) -> None:
        """
        Initialize the input handler.
        
        Args:
            command_callback: Callback function to be called when a command is processed
        """
        self.command_callback = command_callback
    
    def process_command(self, command: str, value: float, source: str) -> None:
        """
        Process a command from any input source.
        
        Args:
            command: Command name
            value: Command value
            source: Command source (e.g., "keyboard", "gamepad")
        """
        print(f"Processing command: {command}, value: {value}, source: {source}")
        
        # Call the command callback if provided
        if self.command_callback:
            self.command_callback(command, value, source)
    
    def validate_command(self, command: str, value: float, source: str) -> bool:
        """
        Validate a command.
        
        Args:
            command: Command name
            value: Command value
            source: Command source (e.g., "keyboard", "gamepad")
            
        Returns:
            True if the command is valid, False otherwise
        """
        # Validate command source
        if source not in ["keyboard", "gamepad", "remote"]:
            print(f"Invalid command source: {source}")
            return False
        
        # Validate command name
        valid_commands = [
            "power_cmd",
            "roll_cmd",
            "pitch_cmd",
            "yaw_cmd",
            "thrust_tilt_cmd",
            "flap_cmd",
            "speedbrake_cmd",
            "landing_gear_cmd",
            "wheel_steer_cmd",
            "wheel_brake_cmd",
            "airspeed_setpoint_kts",
            "heading_setpoint_deg",
            "altitude_setpoint_ft",
        ]
        
        if command not in valid_commands:
            print(f"Invalid command: {command}")
            return False
        
        # Validate command value
        if not isinstance(value, (int, float)):
            print(f"Invalid command value: {value}")
            return False
        
        return True
