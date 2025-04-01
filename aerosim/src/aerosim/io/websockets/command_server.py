"""
Command WebSocket server for AeroSim.

This module provides a WebSocket server for handling control commands from aerosim-app.
"""

import asyncio
import json
import traceback
from typing import Set, Dict, Any, Optional, Callable, Deque
from collections import deque
from dataclasses import dataclass
from websockets import WebSocketServerProtocol
import websockets

# Queue for storing commands received from WebSocket clients
command_queue: Deque[Dict[str, Any]] = deque(maxlen=10)


@dataclass
class ControlCommand:
    """Dataclass for validating and representing control commands"""

    command: str
    value: float
    source: str

    def __post_init__(self):
        """Validate the command data after initialization"""
        if not isinstance(self.command, str):
            raise ValueError("Invalid command: must be a string")

        if not isinstance(self.value, (int, float)):
            raise ValueError("Invalid value: must be a number")

        if self.source not in ["gamepad", "keyboard"]:
            raise ValueError("Invalid source: must be 'gamepad' or 'keyboard'")

        # Validate command is a valid control parameter
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
            "manual_override",
            "left_stick_x",
            "left_stick_y",
            "right_stick_x",
            "right_stick_y",
        ]
        if self.command not in valid_commands:
            raise ValueError(
                f"Invalid command: '{self.command}'. Must be one of {valid_commands}"
            )


async def handle_command_message(
    message: str,
    websocket: WebSocketServerProtocol,
    custom_handler: Optional[Callable] = None,
) -> None:
    """
    Process incoming WebSocket command messages and validate commands.

    Args:
        message: JSON message string
        websocket: WebSocket connection to respond to
        custom_handler: Optional custom handler for command messages
    """
    try:
        data = json.loads(message)

        # Create and validate the command
        command_data = ControlCommand(
            command=data.get("command", ""),
            value=data.get("value", 0),
            source=data.get("source", ""),
        )

        print(
            f"Received {command_data.source} command: {command_data.command} with value: {command_data.value}"
        )

        # Add command to queue
        command_dict = {
            "command": command_data.command,
            "value": command_data.value,
            "source": command_data.source,
        }
        command_queue.append(command_dict)

        # Call custom handler if provided
        if custom_handler:
            await custom_handler(command_dict, websocket)

        # Send acknowledgment
        await websocket.send(
            json.dumps(
                {
                    "status": "received",
                    "command": command_data.command,
                    "value": command_data.value,
                    "source": command_data.source,
                }
            )
        )

    except ValueError as ve:
        print(f"Validation error: {ve}")
        await websocket.send(json.dumps({"status": "error", "message": str(ve)}))
    except json.JSONDecodeError:
        print("Invalid JSON received")
        await websocket.send(
            json.dumps({"status": "error", "message": "Invalid JSON format"})
        )
    except Exception as e:
        print(f"Error processing message: {e}")
        await websocket.send(json.dumps({"status": "error", "message": "Server error"}))


async def handle_command_client(
    websocket: WebSocketServerProtocol,
    clients: Set[WebSocketServerProtocol],
    custom_handler: Optional[Callable] = None,
) -> None:
    """
    Handle WebSocket connections and process command messages.

    Args:
        websocket: WebSocket connection
        clients: Set of connected clients
        custom_handler: Optional custom handler for command messages
    """
    clients.add(websocket)
    print(f"Command client connected! ({len(clients)} clients)")

    try:
        async for message in websocket:
            # Process messages asynchronously
            asyncio.create_task(
                handle_command_message(message, websocket, custom_handler)
            )
    except websockets.exceptions.ConnectionClosed:
        print("Command client disconnected.")
    except Exception as e:
        print(f"Error while processing connection: {e}")
        traceback.print_exc()
    finally:
        clients.remove(websocket)
        print(f"Command client removed. ({len(clients)} clients remaining)")


async def start_command_server(
    port: int = 5001,
    custom_handler: Optional[Callable] = None,
    ping_interval: int = 20,
    ping_timeout: int = 20,
    close_timeout: int = 10,
) -> None:
    """
    Start a WebSocket server for handling control commands.

    Args:
        port: WebSocket server port
        custom_handler: Optional custom handler for command messages
        ping_interval: Interval between pings in seconds
        ping_timeout: Timeout for ping responses in seconds
        close_timeout: Timeout for close handshake in seconds
    """
    clients: Set[WebSocketServerProtocol] = set()

    print(f"Starting command WebSocket server on port {port}...")

    async with websockets.serve(
        lambda ws: handle_command_client(ws, clients, custom_handler),
        "localhost",
        port,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        close_timeout=close_timeout,
    ):
        print(f"Command WebSocket server running on ws://localhost:{port}")
        # Keep the server running indefinitely
        await asyncio.Future()


def get_command_queue() -> Deque[Dict[str, Any]]:
    """
    Get the command queue.

    Returns:
        Queue of commands received from WebSocket clients
    """
    return command_queue
