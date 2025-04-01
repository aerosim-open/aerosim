"""
Flight display management for AeroSim.

This module provides utilities for handling flight display data from the simulation.
"""

from typing import Optional, Callable, Dict, Any

from ..io.websockets.data_server import add_flight_data_to_queue


class FlightDisplayManager:
    """
    Flight display manager for AeroSim.
    
    This class provides utilities for handling flight display data from the simulation.
    """
    
    def __init__(self, data_callback: Optional[Callable] = None) -> None:
        """
        Initialize the flight display manager.
        
        Args:
            data_callback: Callback function to be called when new flight data is received
        """
        self.data_callback = data_callback
        self.latest_data = None
    
    def process_flight_display_data(self, data: Dict[str, Any], _: Any = None) -> None:
        """
        Process flight display data from middleware.
        
        Args:
            data: Flight display data from middleware
            _: Unused parameter
        """
        try:
            # Convert flight display data to the format expected by aerosim-app
            flight_data = {
                "airspeed_kts": data.airspeed_kts,
                "true_airspeed_kts": data.true_airspeed_kts,
                "altitude_ft": data.altitude_ft,
                "target_altitude_ft": data.target_altitude_ft,
                "altimeter_pressure_setting_inhg": data.altimeter_pressure_setting_inhg,
                "vertical_speed_fps": data.vertical_speed_fps,
                "pitch_deg": data.pitch_deg,
                "roll_deg": data.roll_deg,
                "side_slip_fps2": data.side_slip_fps2,
                "heading_deg": data.heading_deg,
                "hsi_course_select_heading_deg": data.hsi_course_select_heading_deg,
                "hsi_course_deviation_deg": data.hsi_course_deviation_deg,
                "hsi_mode": data.hsi_mode
            }
            
            # Store the latest flight data
            self.latest_data = flight_data
            
            # Add the flight data to the WebSocket queue for streaming
            add_flight_data_to_queue(flight_data)
            
            # Call the data callback if provided
            if self.data_callback:
                self.data_callback(flight_data)
                
        except Exception as e:
            print(f"Error processing flight display data: {e}")
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest flight display data.
        
        Returns:
            The latest flight display data as a dictionary, or None if no data has been received
        """
        return self.latest_data


def on_flight_display_data(data: Dict[str, Any], _: Any = None) -> None:
    """
    Callback function for processing flight display data from middleware.
    
    This function is designed to be used as a callback for aerosim_data middleware.
    It creates a FlightDisplayManager instance if one doesn't exist and processes the flight display data.
    
    Args:
        data: Flight display data from middleware
        _: Unused parameter
    """
    # Create a global flight display manager if one doesn't exist
    global _flight_display_manager
    if '_flight_display_manager' not in globals():
        _flight_display_manager = FlightDisplayManager()
    
    # Process the flight display data
    _flight_display_manager.process_flight_display_data(data, _)
