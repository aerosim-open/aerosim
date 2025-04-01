"""
Image WebSocket server for AeroSim.

This module provides a WebSocket server for streaming camera images to aerosim-app.
"""

import asyncio
import traceback
import base64
import time
import numpy as np
import cv2
from typing import Set, Dict, Any, Optional, Callable, Deque
from collections import deque
from websockets import WebSocketServerProtocol
import websockets

from aerosim_data import types as aerosim_types
from aerosim_data import middleware

# Initialize bincode serializer
serializer = middleware.BincodeSerializer()

# Queue for storing images to be sent to WebSocket clients
image_queue: Deque[np.ndarray] = deque(maxlen=5)

async def handle_image_client(
    websocket: WebSocketServerProtocol,
    clients: Set[WebSocketServerProtocol],
    custom_handler: Optional[Callable] = None
) -> None:
    """
    Handle WebSocket connections for image streaming.
    
    Args:
        websocket: WebSocket connection
        clients: Set of connected clients
        custom_handler: Optional custom handler for image streaming
    """
    clients.add(websocket)
    print(f"Image client connected! ({len(clients)} clients)")
    
    try:
        while True:
            if custom_handler:
                # Use custom handler if provided
                await custom_handler(websocket)
            else:
                # Default image streaming behavior
                if image_queue:
                    # Get the latest image from the queue
                    image = image_queue.pop()
                    
                    # Encode image to JPEG and then to base64
                    _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    encoded_image = base64.b64encode(buffer).decode("utf-8")
                    
                    # Send encoded image to client
                    await websocket.send(encoded_image)
                
                # Short sleep to prevent CPU overuse
                await asyncio.sleep(0.05)
                
    except websockets.exceptions.ConnectionClosed:
        print("Image client disconnected.")
    except Exception as e:
        print(f"Error in image streaming: {e}")
        traceback.print_exc()
    finally:
        clients.remove(websocket)
        print(f"Image client removed. ({len(clients)} clients remaining)")

async def start_image_server(
    port: int = 5002,
    custom_handler: Optional[Callable] = None,
    ping_interval: int = 20,
    ping_timeout: int = 20,
    close_timeout: int = 10
) -> None:
    """
    Start a WebSocket server for streaming camera images.
    
    Args:
        port: WebSocket server port
        custom_handler: Optional custom handler for image streaming
        ping_interval: Interval between pings in seconds
        ping_timeout: Timeout for ping responses in seconds
        close_timeout: Timeout for close handshake in seconds
    """
    clients: Set[WebSocketServerProtocol] = set()
    
    print(f"Starting image WebSocket server on port {port}...")
    
    async with websockets.serve(
        lambda ws: handle_image_client(ws, clients, custom_handler),
        "localhost",
        port,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        close_timeout=close_timeout
    ):
        print(f"Image WebSocket server running on ws://localhost:{port}")
        # Keep the server running indefinitely
        await asyncio.Future()

def add_image_to_queue(image: np.ndarray) -> None:
    """
    Add an image to the queue for streaming to WebSocket clients.
    
    Args:
        image: Image as a NumPy array
    """
    # Check if image is None
    if image is None:
        return
        
    image_queue.append(image)

def on_camera_data(payload: bytes) -> None:
    """
    Process camera data from middleware and add to image queue.
    
    This function is designed to be used as a callback for aerosim_data middleware.
    
    Args:
        payload: Raw camera data from middleware
    """
    try:
        # Deserialize the message using the proper type
        _, data = serializer.deserialize_message(aerosim_types.CompressedImage, payload)
        
        # Convert bytes to NumPy array
        image_array = np.frombuffer(data.data, dtype=np.uint8)
        
        # Decode the image
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is not None and img.size > 0:
            # Process image for display (resize if needed)
            max_dim = 800
            h, w = img.shape[:2]
            if h > max_dim or w > max_dim:
                scale = max_dim / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
            
            # Add the image to the queue for streaming
            add_image_to_queue(img)
            
    except Exception as e:
        print(f"Error processing camera data: {e}")
        traceback.print_exc()
