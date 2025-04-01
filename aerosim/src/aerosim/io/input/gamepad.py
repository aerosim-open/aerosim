"""
Gamepad input handler for AeroSim.

This module provides utilities for handling gamepad input.
"""

import pygame
from typing import Callable, Optional

from .base import InputHandler


class GamepadHandler(InputHandler):
    """
    Gamepad input handler for AeroSim.

    This class provides utilities for handling gamepad input for flight control.
    """

    def __init__(self, command_callback: Optional[Callable] = None) -> None:
        """
        Initialize the gamepad input handler.

        Args:
            command_callback: Callback function to be called when a command is processed
        """
        super().__init__(command_callback)

        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()

        # Initialize joystick module
        pygame.joystick.init()

        # Store joystick
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Connected to joystick: {self.joystick.get_name()}")
        else:
            print("No joystick connected.")

        # Define axis mappings (for Xbox controller)
        self.axis_map = [
            ("left_stick_x", 0, 1.0),  # Left stick horizontal axis
            ("left_stick_y", 1, 1.0),  # Left stick vertical axis
            ("right_stick_x", 2, 1.0),  # Right stick horizontal axis
            ("right_stick_y", 3, 1.0),  # Right stick vertical axis
        ]

        # Define button mappings (for Xbox controller)
        self.button_map = [
            ("power_cmd", 3, 1.0),  # Y button (increase power)
            ("power_cmd", 0, -1.0),  # A button (decrease power)
            ("wheel_steer_cmd", 6, -1.0),  # LB button (steer left)
            ("wheel_steer_cmd", 7, 1.0),  # RB button (steer right)
            ("wheel_brake_cmd", 4, 1.0),  # LT button (apply brake)
            ("wheel_brake_cmd", 5, -1.0),  # RT button (release brake)
            ("manual_override", 1, 1.0),  # B button (manual override)
        ]

        # Store last sent values to avoid sending duplicate commands
        self.last_values = {}

        # Define deadzone for joystick axes
        self.deadzone = 0.1

        # Define scale factors for joystick inputs (now uniform 1.0)
        self.scale_factors = {
            "left_stick_x": 1.0,
            "left_stick_y": 1.0,
            "right_stick_x": 1.0,
            "right_stick_y": 1.0,
        }

        # Define step value for button inputs
        self.button_step = 0.02

    def handle_axis(self, axis: int, value: float) -> None:
        """
        Handle a joystick axis event.

        Args:
            axis: Axis index
            value: Axis value (-1.0 to 1.0)
        """
        # Find the command for this axis
        for command, axis_idx, direction in self.axis_map:
            if axis == axis_idx:
                # Apply deadzone
                if abs(value) < self.deadzone:
                    value = 0.0

                # Apply direction and scale factor
                scaled_value = value * direction * self.scale_factors.get(command, 1.0)

                # Only send if the value has changed significantly
                if (
                    command not in self.last_values
                    or abs(self.last_values[command] - scaled_value) > 0.05
                ):
                    self.last_values[command] = scaled_value
                    self.process_command(command, scaled_value, "gamepad")

                break

    def handle_button(self, button: int, pressed: bool) -> None:
        """
        Handle a joystick button event.

        Args:
            button: Button index
            pressed: True if the button was pressed, False if released
        """
        # Find the command for this button
        for command, button_idx, direction in self.button_map:
            if button == button_idx:
                # Only process if the button is pressed
                if pressed:
                    value = direction * self.button_step
                    self.process_command(command, value, "gamepad")

                break

    def update(self) -> bool:
        """
        Update the gamepad input handler.

        This method should be called in the main loop to process gamepad events.

        Returns:
            True if the update was successful, False if the application should exit
        """
        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        # If no joystick is connected, try to connect one
        if self.joystick is None:
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                print(f"Connected to joystick: {self.joystick.get_name()}")
            else:
                return True

        # Process joystick axes
        for command, axis_idx, direction in self.axis_map:
            if axis_idx < self.joystick.get_numaxes():
                value = self.joystick.get_axis(axis_idx)
                self.handle_axis(axis_idx, value)

        # Process joystick buttons
        for command, button_idx, direction in self.button_map:
            if button_idx < self.joystick.get_numbuttons():
                pressed = self.joystick.get_button(button_idx)
                self.handle_button(button_idx, pressed)

        return True
