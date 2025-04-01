"""
Camera management for AeroSim.

This module provides utilities for handling camera data from the simulation.
"""

import cv2
import numpy as np
import base64
from typing import Optional, Callable, Dict, Any

from ..io.websockets.image_server import add_image_to_queue


class CameraManager:
    """
    Camera manager for AeroSim.
    
    This class provides utilities for handling camera data from the simulation.
    """
    
    def __init__(self, image_callback: Optional[Callable] = None) -> None:
        """
        Initialize the camera manager.
        
        Args:
            image_callback: Callback function to be called when a new image is received
        """
        self.image_callback = image_callback
        self.latest_image = None
    
    def process_camera_data(self, payload: bytes) -> None:
        """
        Process camera data from middleware.
        
        Args:
            payload: Raw camera data from middleware
        """
        try:
            # Decode the image from the payload
            # This assumes the payload is a JPEG image encoded in base64
            jpg_as_text = base64.b64decode(payload)
            jpg_as_np = np.frombuffer(jpg_as_text, dtype=np.uint8)
            image = cv2.imdecode(jpg_as_np, flags=1)
            
            # Store the latest image
            self.latest_image = image
            
            # Add the image to the WebSocket queue for streaming
            add_image_to_queue(image)
            
            # Call the image callback if provided
            if self.image_callback:
                self.image_callback(image)
                
        except Exception as e:
            print(f"Error processing camera data: {e}")
    
    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Get the latest camera image.
        
        Returns:
            The latest camera image as a NumPy array, or None if no image has been received
        """
        return self.latest_image
    
    def save_image(self, filename: str) -> bool:
        """
        Save the latest camera image to a file.
        
        Args:
            filename: Path to save the image
            
        Returns:
            True if the image was saved successfully, False otherwise
        """
        if self.latest_image is None:
            print("No image to save")
            return False
        
        try:
            cv2.imwrite(filename, self.latest_image)
            print(f"Image saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False


def on_camera_data(payload: bytes) -> None:
    """
    Callback function for processing camera data from middleware.
    
    This function is designed to be used as a callback for aerosim_data middleware.
    It creates a CameraManager instance if one doesn't exist and processes the camera data.
    
    Args:
        payload: Raw camera data from middleware
    """
    # Create a global camera manager if one doesn't exist
    global _camera_manager
    if '_camera_manager' not in globals():
        _camera_manager = CameraManager()
    
    # Process the camera data
    _camera_manager.process_camera_data(payload)
