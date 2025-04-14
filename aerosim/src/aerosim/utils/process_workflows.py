#!/usr/bin/env python3
"""
Process Workflows for Utils

This module defines functions to run complete processing workflows for three use cases:
  1. OpenADSB workflow (real ADS-B data processing)
  2. Artificial track generation workflow
  3. Google Earth KML workflow

Each workflow performs the following steps:
  - Convert raw data to CSV (or use an existing CSV file)
  - Filter or process the CSV into trajectory JSON files
  - Create a simulation scenario JSON from the trajectories
  - Visualize the tracks (e.g. as a combined Folium map)
  - Generate scenario reports and trajectory plots
"""

import json
from pathlib import Path
from datetime import timedelta, timezone, datetime

from utils import (
    conversion,
    scenario_generator,
    visualization,
    ArtificialTrackGenerator,
    scenario_report,
)
from utils.tracks_from_map import parse_kml, generate_csv_from_tracks

# Set up default directories (you may also load these from a configuration file)
DEFAULT_INPUT_DIR = Path("../inputs")
DEFAULT_OUTPUT_DIR = Path("../outputs")
DEFAULT_TRACKS_DIR = Path("../tracks")
DEFAULT_TRAJECTORIES_DIR = Path("../trajectories")
DEFAULT_VISUALIZATION_DIR = Path("../visualization")
DEFAULT_FOLIUM_DIR = Path("../visualization/folium")
DEFAULT_REPORTS_DIR = Path("../reports")

# Create folders if they do not exist
for folder in [DEFAULT_OUTPUT_DIR, DEFAULT_TRACKS_DIR, DEFAULT_TRAJECTORIES_DIR, 
              DEFAULT_VISUALIZATION_DIR, DEFAULT_FOLIUM_DIR, DEFAULT_REPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


def process_openadsb_workflow(
    input_json: Path = None,
    center_lat: float = 34.217411,
    center_lon: float = -118.491081,
    radius_km: float = 5,
    num_vehicles: int = None,
    interval: int = 10,
    generate_report: bool = True,
    report_output: Path = None,
    plot_trajectories: bool = True,
    plot_output: Path = None,
) -> dict:
    """
    Process workflow for ADS-B data.
    
    Steps:
      1. Convert raw ADS-B JSON data to CSV.
      2. Filter tracks around a reference point.
      3. Convert filtered track CSV files into trajectory JSON files.
      4. Generate a simulation scenario JSON from trajectories.
      5. Visualize the tracks.
      6. Generate scenario report and trajectory plot (optional).
    
    Args:
        input_json: Path to the input ADS-B JSON file. If not provided, the first JSON in inputs/ is used.
        center_lat: Reference latitude for filtering.
        center_lon: Reference longitude for filtering.
        radius_km: Search radius in kilometers.
        num_vehicles: (Optional) Number of vehicles to include in the scenario.
        interval: Time interval (seconds) between points for the scenario.
        generate_report: Whether to generate a markdown report.
        report_output: Path for the markdown report. If None, uses default location.
        plot_trajectories: Whether to generate a trajectory plot.
        plot_output: Path for the trajectory plot. If None, uses default location.
    
    Returns:
        The generated scenario as a Python dictionary.
    """
    # Use first JSON file in DEFAULT_INPUT_DIR if input not provided.
    if input_json is None:
        json_files = list(DEFAULT_INPUT_DIR.glob("*.json"))
        if not json_files:
            raise FileNotFoundError("No JSON files found in the inputs folder.")
        input_json = json_files[0]
        print(f"No input JSON provided. Using {input_json}")
    
    csv_path = DEFAULT_OUTPUT_DIR / "output.csv"
    conversion.convert_json_to_csv(str(input_json), str(csv_path))
    
    filtered_csv = DEFAULT_OUTPUT_DIR / "filtered_tracks.csv"
    conversion.filter_tracks(
        input_csv_path=str(csv_path),
        filtered_csv_path=str(filtered_csv),
        tracks_folder=str(DEFAULT_TRACKS_DIR),
        ref_lat=center_lat,
        ref_lon=center_lon,
        ref_range_m=radius_km * 1000,
    )
    
    # Convert filtered track CSV files to trajectory JSON files
    conversion.convert_tracks_to_json(str(DEFAULT_TRACKS_DIR), str(DEFAULT_TRAJECTORIES_DIR))
    
    # Generate scenario JSON from trajectory JSON files
    scenario_json_file = DEFAULT_OUTPUT_DIR / "scenario.json"
    scenario_generator.generate_scenario_json(str(DEFAULT_TRAJECTORIES_DIR), str(scenario_json_file))
    
    # Visualize the tracks (Folium map)
    visualization.visualize_folder(str(DEFAULT_TRACKS_DIR), str(DEFAULT_VISUALIZATION_DIR / "folium" / "combined_map.html"), method="folium")
    
    with open(scenario_json_file, 'r') as f:
        scenario_data = json.load(f)
    
    # Generate report and plot if requested
    if generate_report:
        if report_output is None:
            report_output = DEFAULT_REPORTS_DIR / "scenario_report.md"
        report_md = scenario_report.generate_markdown_report(scenario_data)
        scenario_report.save_markdown_report(report_md, str(report_output))
        print(f"Scenario report saved to {report_output}")
        
        if plot_trajectories:
            if plot_output is None:
                plot_output = DEFAULT_REPORTS_DIR / "trajectories.png"
            scenario_report.plot_trajectories(scenario_data, str(plot_output))
            print(f"Trajectory plot saved to {plot_output}")
    
    return scenario_data


def process_artificial_workflow(
    maneuver: str = "elliptical",
    num_tracks: int = 3,
    center_lat: float = 34.217411,
    center_lon: float = -118.491081,
    center_alt: float = 1000,
    separation: float = 0.005,
    time_delay: int = 30,
    num_points: int = 20,
    interval_seconds: int = 10,
    generate_report: bool = True,
    report_output: Path = None,
    plot_trajectories: bool = True,
    plot_output: Path = None,
) -> dict:
    """
    Process workflow for generating artificial tracks.
    
    Steps:
      1. Generate artificial tracks using the specified maneuver.
      2. Save the tracks to a CSV file.
      3. Convert the CSV (with multiple track IDs) to trajectory JSON files.
      4. Generate a simulation scenario JSON from trajectories.
      5. Visualize the tracks.
      6. Generate scenario report and trajectory plot (optional).
    
    Args:
        maneuver: Track pattern type (random, circular, elliptical, flyby, square, rectangle, zigzag, spiral).
        num_tracks: Number of tracks to generate.
        center_lat, center_lon, center_alt: Center coordinates and altitude.
        separation: Separation distance in degrees between independent tracks.
        time_delay: Time delay in seconds between tracks.
        num_points: Number of points per track.
        interval_seconds: Time interval in seconds between points.
        generate_report: Whether to generate a markdown report.
        report_output: Path for the markdown report. If None, uses default location.
        plot_trajectories: Whether to generate a trajectory plot.
        plot_output: Path for the trajectory plot. If None, uses default location.
    
    Returns:
        The generated scenario as a Python dictionary.
    """
    # Instantiate the artificial track generator with given parameters.
    generator = ArtificialTrackGenerator(
        num_tracks=num_tracks,
        track_generator_class=maneuver,
        center_lat=center_lat,
        center_lon=center_lon,
        center_alt=center_alt,
        separation_distance=separation,
        time_delay=time_delay,
        min_alt=center_alt * 0.9,
        max_alt=center_alt * 1.1,
        fly_along=False,
        num_points=num_points,
        interval_seconds=interval_seconds,
    )
    generator.generate()
    artificial_csv = DEFAULT_OUTPUT_DIR / "artificial_tracks.csv"
    generator.save_to_csv(str(artificial_csv))
    
    # Process the artificial CSV file to generate trajectory JSON files.
    conversion.convert_tracks_to_json(str(DEFAULT_OUTPUT_DIR), str(DEFAULT_TRAJECTORIES_DIR))
    
    scenario_json_file = DEFAULT_OUTPUT_DIR / "scenario_artificial.json"
    scenario_generator.generate_scenario_json(str(DEFAULT_TRAJECTORIES_DIR), str(scenario_json_file))
    
    # Visualize the artificial tracks
    visualization.visualize_folder(str(DEFAULT_OUTPUT_DIR), str(DEFAULT_VISUALIZATION_DIR / "folium" / "combined_map_artificial.html"), method="folium")
    
    with open(scenario_json_file, 'r') as f:
        scenario_data = json.load(f)
    
    # Generate report and plot if requested
    if generate_report:
        if report_output is None:
            report_output = DEFAULT_REPORTS_DIR / "scenario_report_artificial.md"
        report_md = scenario_report.generate_markdown_report(scenario_data)
        scenario_report.save_markdown_report(report_md, str(report_output))
        print(f"Scenario report saved to {report_output}")
        
        if plot_trajectories:
            if plot_output is None:
                plot_output = DEFAULT_REPORTS_DIR / "trajectories_artificial.png"
            scenario_report.plot_trajectories(scenario_data, str(plot_output))
            print(f"Trajectory plot saved to {plot_output}")
    
    return scenario_data


def process_kml_workflow(
    input_kml: Path,
    interval: int = 10,
    generate_report: bool = True,
    report_output: Path = None,
    plot_trajectories: bool = True,
    plot_output: Path = None,
) -> dict:
    """
    Process workflow for tracks created in Google Earth (KML).
    
    Steps:
      1. Convert the KML file to CSV using tracks-from-map functionality.
      2. Convert the resulting CSV to trajectory JSON files.
      3. Generate a simulation scenario JSON from the trajectories.
      4. Visualize the tracks.
      5. Generate scenario report and trajectory plot (optional).
    
    Args:
        input_kml: Path to the KML file exported from Google Earth.
        interval: Time interval in seconds between track points.
        generate_report: Whether to generate a markdown report.
        report_output: Path for the markdown report. If None, uses default location.
        plot_trajectories: Whether to generate a trajectory plot.
        plot_output: Path for the trajectory plot. If None, uses default location.
    
    Returns:
        The generated scenario as a Python dictionary.
    """
    from utils.tracks_from_map import parse_kml, generate_csv_from_tracks

    # Parse the KML file to get track data
    tracks = parse_kml(str(input_kml))
    if not tracks:
        raise ValueError("No tracks found in the provided KML file.")
    
    kml_csv = DEFAULT_OUTPUT_DIR / "kml_output.csv"
    generate_csv_from_tracks(tracks, str(kml_csv), interval_seconds=interval)
    
    # Convert the generated CSV to trajectory JSON files.
    conversion.convert_tracks_to_json(str(DEFAULT_OUTPUT_DIR), str(DEFAULT_TRAJECTORIES_DIR))
    
    scenario_json_file = DEFAULT_OUTPUT_DIR / "scenario_kml.json"
    scenario_generator.generate_scenario_json(str(DEFAULT_TRAJECTORIES_DIR), str(scenario_json_file))
    
    # Visualize the tracks
    visualization.visualize_folder(str(DEFAULT_OUTPUT_DIR), str(DEFAULT_VISUALIZATION_DIR / "folium" / "combined_map_kml.html"), method="folium")
    
    with open(scenario_json_file, 'r') as f:
        scenario_data = json.load(f)
    
    # Generate report and plot if requested
    if generate_report:
        if report_output is None:
            report_output = DEFAULT_REPORTS_DIR / "scenario_report_kml.md"
        report_md = scenario_report.generate_markdown_report(scenario_data)
        scenario_report.save_markdown_report(report_md, str(report_output))
        print(f"Scenario report saved to {report_output}")
        
        if plot_trajectories:
            if plot_output is None:
                plot_output = DEFAULT_REPORTS_DIR / "trajectories_kml.png"
            scenario_report.plot_trajectories(scenario_data, str(plot_output))
            print(f"Trajectory plot saved to {plot_output}")
    
    return scenario_data


def main():
    """
    Run all three workflows sequentially:
      1. OpenADSB Workflow
      2. Artificial Track Workflow
      3. Google Earth KML Workflow
    """
    # print("=== Running OpenADSB Workflow ===")
    # openadsb_scenario = process_openadsb_workflow()
    # print("OpenADSB Scenario generated.")

    print("\n=== Running Artificial Track Workflow ===")
    artificial_scenario = process_artificial_workflow()
    print("Artificial Track Scenario generated.")


    # Optionally, save or further process the scenarios.
    print("\nAll workflows completed.")


if __name__ == "__main__":
    main()
