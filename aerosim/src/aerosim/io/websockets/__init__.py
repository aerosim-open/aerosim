"""
WebSockets integration for AeroSim.

This module provides standardized WebSockets servers for communication with aerosim-app.
"""

import asyncio
from typing import List, Dict, Any, Set, Callable, Optional
import os

from .command_server import start_command_server
from .image_server import start_image_server
from .data_server import start_data_server

# Default WebSockets ports
DEFAULT_COMMAND_PORT = int(os.environ.get("AEROSIM_APP_WS_PORT", "5001"))
DEFAULT_IMAGE_PORT = DEFAULT_COMMAND_PORT + 1  # 5002
DEFAULT_DATA_PORT = DEFAULT_COMMAND_PORT + 2   # 5003

async def start_websocket_servers(
    command_port: int = DEFAULT_COMMAND_PORT,
    image_port: int = DEFAULT_IMAGE_PORT,
    data_port: int = DEFAULT_DATA_PORT,
    command_handler: Optional[Callable] = None,
    image_handler: Optional[Callable] = None,
    data_handler: Optional[Callable] = None
) -> List[asyncio.Task]:
    """
    Start all WebSockets servers for communication with aerosim-app.
    
    Args:
        command_port: Port for the command WebSocket server
        image_port: Port for the image WebSocket server
        data_port: Port for the flight data WebSocket server
        command_handler: Custom handler for command messages
        image_handler: Custom handler for image messages
        data_handler: Custom handler for flight data messages
        
    Returns:
        List of asyncio tasks for the WebSockets servers
    """
    tasks = []
    
    # Configure WebSocket server with more robust settings
    ping_interval = 30  # Send ping every 30 seconds
    ping_timeout = 10   # Wait 10 seconds for pong response
    close_timeout = 5   # Wait 5 seconds for close handshake
    
    # Start command server
    command_task = asyncio.create_task(
        start_command_server(
            command_port, 
            command_handler,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            close_timeout=close_timeout
        )
    )
    tasks.append(command_task)
    
    # Start image server
    image_task = asyncio.create_task(
        start_image_server(
            image_port, 
            image_handler,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            close_timeout=close_timeout
        )
    )
    tasks.append(image_task)
    
    # Start data server
    data_task = asyncio.create_task(
        start_data_server(
            data_port, 
            data_handler,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            close_timeout=close_timeout
        )
    )
    tasks.append(data_task)
    
    return tasks

__all__ = [
    "start_websocket_servers",
    "start_command_server",
    "start_image_server",
    "start_data_server",
    "DEFAULT_COMMAND_PORT",
    "DEFAULT_IMAGE_PORT",
    "DEFAULT_DATA_PORT"
]
