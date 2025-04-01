"""
Flight data WebSocket server for AeroSim.

This module provides a WebSocket server for sending flight data to aerosim-app.
"""

import asyncio
import json
import traceback
from typing import Set, Dict, Any, Optional, Callable, Deque
from collections import deque
from websockets import WebSocketServerProtocol
import websockets

# Queue for storing flight data to be sent to WebSocket clients
data_queue: Deque[Dict[str, Any]] = deque(maxlen=1)

async def handle_data_client(
    websocket: WebSocketServerProtocol,
    clients: Set[WebSocketServerProtocol],
    custom_handler: Optional[Callable] = None
) -> None:
    """
    Handle WebSocket connections for flight data transfer.
    
    Args:
        websocket: WebSocket connection
        clients: Set of connected clients
        custom_handler: Optional custom handler for flight data
    """
    clients.add(websocket)
    print(f"Flight data client connected! ({len(clients)} clients)")
    
    try:
        while True:
            if custom_handler:
                # Use custom handler if provided
                await custom_handler(websocket)
            else:
                # Default flight data behavior
                if data_queue:
                    data = data_queue.pop()
                    
                    # Send flight data to client
                    await websocket.send(json.dumps(data))
                
                # Short sleep to prevent CPU overuse
                await asyncio.sleep(0.1)
                
    except websockets.exceptions.ConnectionClosed:
        print("Flight data client disconnected.")
    except Exception as e:
        print(f"Error in flight data streaming: {e}")
        traceback.print_exc()
    finally:
        clients.remove(websocket)
        print(f"Flight data client removed. ({len(clients)} clients remaining)")

async def start_data_server(
    port: int = 5003,
    custom_handler: Optional[Callable] = None,
    ping_interval: int = 20,
    ping_timeout: int = 20,
    close_timeout: int = 10
) -> None:
    """
    Start a WebSocket server for sending flight data.
    
    Args:
        port: WebSocket server port
        custom_handler: Optional custom handler for flight data
        ping_interval: Interval between pings in seconds
        ping_timeout: Timeout for ping responses in seconds
        close_timeout: Timeout for close handshake in seconds
    """
    clients: Set[WebSocketServerProtocol] = set()
    
    print(f"Starting flight data WebSocket server on port {port}...")
    
    async with websockets.serve(
        lambda ws: handle_data_client(ws, clients, custom_handler),
        "localhost",
        port,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        close_timeout=close_timeout
    ):
        print(f"Flight data WebSocket server running on ws://localhost:{port}")
        # Keep the server running indefinitely
        await asyncio.Future()

def add_flight_data_to_queue(data: Dict[str, Any]) -> None:
    """
    Add flight data to the queue for sending to WebSocket clients.
    
    Args:
        data: Flight data dictionary
    """
    data_queue.append(data)

def on_flight_display_data(data: Dict[str, Any], _: Any) -> None:
    """
    Process flight display data from middleware and add to data queue.
    
    This function is designed to be used as a callback for aerosim_data middleware.
    
    Args:
        data: Flight display data from middleware
        _: Unused parameter
    """
    try:
        # Convert flight display data to the format expected by aerosim-app
        # Convert HSIMode to string to avoid JSON serialization issues
        hsi_mode_value = str(data.hsi_mode)
        if hasattr(data.hsi_mode, 'name'):
            hsi_mode_value = data.hsi_mode.name
        
        flight_data = {
            "airspeed_kts": data.airspeed_kts,
            "true_airspeed_kts": data.true_airspeed_kts,
            "altitude_ft": data.altitude_ft,
            "target_altitude_ft": data.target_altitude_ft,
            "altimeter_pressure_setting_inhg": data.altimeter_pressure_setting_inhg,
            "vertical_speed_fpm": data.vertical_speed_fpm,
            "pitch_deg": data.pitch_deg,
            "roll_deg": data.roll_deg,
            "side_slip_fps2": data.side_slip_fps2,
            "heading_deg": data.heading_deg,
            "hsi_course_select_heading_deg": data.hsi_course_select_heading_deg,
            "hsi_course_deviation_deg": data.hsi_course_deviation_deg,
            "hsi_mode": hsi_mode_value
        }
        
        # Add the flight data to the queue for streaming
        add_flight_data_to_queue(flight_data)
    except Exception as e:
        print(f"Error processing flight display data: {e}")
        traceback.print_exc()
