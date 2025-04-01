"""
Keyboard input handler for AeroSim.

This module provides utilities for handling keyboard input.
"""

import pygame
from typing import Dict, Any, Callable, Optional, Tuple

from .base import InputHandler


class KeyboardHandler(InputHandler):
    """
    Keyboard input handler for AeroSim.
    
    This class provides utilities for handling keyboard input for flight control.
    """
    
    def __init__(self, command_callback: Optional[Callable] = None) -> None:
        """
        Initialize the keyboard input handler.
        
        Args:
            command_callback: Callback function to be called when a command is processed
        """
        super().__init__(command_callback)
        
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
        
        # Define keyboard mappings
        self.key_map = {
            pygame.K_UP: ("airspeed_setpoint_kts", +1),  # Increase airspeed
            pygame.K_DOWN: ("airspeed_setpoint_kts", -1),  # Decrease airspeed
            pygame.K_a: ("heading_setpoint_deg", -1),  # Turn left
            pygame.K_d: ("heading_setpoint_deg", +1),  # Turn right
            pygame.K_w: ("altitude_setpoint_ft", +1),  # Increase altitude
            pygame.K_s: ("altitude_setpoint_ft", -1),  # Decrease altitude
        }
        
        # Constants for the keyboard control of autopilot setpoints
        self.AIRSPEED_STEP = 5.0  # kts
        self.ALTITUDE_STEP = 50.0  # ft
        self.HEADING_STEP = 5.0  # deg
        
    def handle_key_event(self, key: int, pressed: bool) -> None:
        """
        Handle a keyboard event.
        
        Args:
            key: Pygame key code
            pressed: True if the key was pressed, False if released
        """
        if not pressed:
            return
        
        if key in self.key_map:
            command, direction = self.key_map[key]
            value = direction
            
            # Scale the value based on the command
            if command == "airspeed_setpoint_kts":
                value *= self.AIRSPEED_STEP
            elif command == "altitude_setpoint_ft":
                value *= self.ALTITUDE_STEP
            elif command == "heading_setpoint_deg":
                value *= self.HEADING_STEP
            
            # Process the command
            self.process_command(command, value, "keyboard")
    
    def update(self) -> None:
        """
        Update the keyboard input handler.
        
        This method should be called in the main loop to process keyboard events.
        """
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                self.handle_key_event(event.key, True)
            elif event.type == pygame.QUIT:
                pygame.quit()
                return False
        
        return True
