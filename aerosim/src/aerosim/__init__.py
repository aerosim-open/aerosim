"""
AeroSim
"""

from .core.simulation import AeroSim
from .core.config import SimConfig
from .io.websockets import start_websocket_servers
from .io.input import InputHandler, KeyboardHandler, GamepadHandler
from .visualization import CameraManager, FlightDisplayManager
from .utils import (
    # Helper functions
    clamp, normalize_heading_deg, distance_m_bearing_deg,
    
    # Track generation
    ArtificialTrackGenerator,
    
    # Conversion functions
    convert_json_to_csv, filter_tracks, convert_tracks_to_json, process_csv,
    
    # Scenario generation
    generate_scenario_json,
    
    # Reporting
    generate_markdown_report, save_markdown_report, plot_trajectories,
    
    # Map track processing
    extract_track_id, parse_kml, generate_csv_from_tracks,
    
    # Coordinate conversion
    geodetic_to_ecef, ecef_to_geodetic, lla_to_ned, ned_to_lla,
    haversine_distance, euclidean_distance_lla, bearing_between_points,
    
    # Visualization
    visualize_folder, plot_tracks,
    
    # Workflows
    process_openadsb_workflow, process_artificial_workflow, process_kml_workflow,
    
    # Configuration
    Config
)

__all__ = [
    "AeroSim",
    "SimConfig",
    "start_websocket_servers",
    "InputHandler",
    "KeyboardHandler", 
    "GamepadHandler",
    "CameraManager",
    "FlightDisplayManager",
    
    # Helper functions
    "clamp",
    "normalize_heading_deg",
    "distance_m_bearing_deg",
    
    # Track generation
    "ArtificialTrackGenerator",
    
    # Conversion functions
    "convert_json_to_csv",
    "filter_tracks",
    "convert_tracks_to_json",
    "process_csv",
    
    # Scenario generation
    "generate_scenario_json",
    
    # Reporting
    "generate_markdown_report",
    "save_markdown_report",
    "plot_trajectories",
    
    # Map track processing
    "extract_track_id",
    "parse_kml",
    "generate_csv_from_tracks",
    
    # Coordinate conversion
    "geodetic_to_ecef",
    "ecef_to_geodetic",
    "lla_to_ned",
    "ned_to_lla",
    "haversine_distance",
    "euclidean_distance_lla",
    "bearing_between_points",
    
    # Visualization
    "visualize_folder",
    "plot_tracks",
    
    # Workflows
    "process_openadsb_workflow",
    "process_artificial_workflow",
    "process_kml_workflow",
    
    # Configuration
    "Config"
]
