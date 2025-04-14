"""
Utils - A suite of tools for aircraft trajectory and scenario generation.

This package provides tools for:
- Converting between different trajectory formats (JSON, CSV, KML)
- Generating artificial aircraft tracks
- Processing real ADS-B data
- Creating simulation scenarios
- Visualizing trajectories
- Generating reports and plots

The package includes a configuration system that can be managed through the CLI
or programmatically. Default settings can be overridden through a config file
or environment variables.
"""

# utils/__init__.py

from .helpers import clamp, normalize_heading_deg, distance_m_bearing_deg
from .artificial_tracks import ArtificialTrackGenerator
from .conversion import (
    convert_json_to_csv,
    filter_tracks,
    convert_tracks_to_json,
    process_csv
)
from .scenario_generator import generate_scenario_json
from .scenario_report import (
    generate_markdown_report,
    save_markdown_report,
    plot_trajectories
)
from .tracks_from_map import (
    extract_track_id,
    parse_kml,
    generate_csv_from_tracks
)
from .utils import (
    geodetic_to_ecef,
    ecef_to_geodetic,
    lla_to_ned,
    ned_to_lla,
    haversine_distance,
    euclidean_distance_lla,
    bearing_between_points
)
from .visualization import visualize_folder, plot_tracks
from .process_workflows import (
    process_openadsb_workflow,
    process_artificial_workflow,
    process_kml_workflow
)
from .config import Config

__all__ = [
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
    "generate_scenario_json"
    
    # Reporting
    "generate_markdown_report",
    "save_markdown_report",
    "plot_trajectories"
    
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

__version__ = '0.1.0'
__author__ = 'Aerosim'
__license__ = 'MIT'
__description__ = 'A suite of tools for aircraft trajectory and scenario generation'
