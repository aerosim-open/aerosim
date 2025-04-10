#!/usr/bin/env python3
import click
import json
from aerosim_utils import (
    convert_json_to_csv,
    filter_tracks,
    convert_tracks_to_json,
    visualize_folder,
    generate_scenario_json,
    ArtificialTrackGenerator,
    process_openadsb_workflow,
    process_artificial_workflow,
    process_kml_workflow
)
from pathlib import Path
import os

@click.group()
def cli():
    """Aerosim Utils - Tools for trajectory conversion, visualization, scenario generation, and track generation."""
    pass

# ------------------ ADS-B Data Commands ------------------
@cli.group()
def adsb():
    """Commands for processing ADS-B data."""
    pass

@adsb.command(name="json2csv")
@click.option('-i', '--input', required=True, help='Input ADS-B JSON file path')
@click.option('-o', '--output', required=True, help='Output CSV file path')
def json_to_csv(input, output):
    """Convert ADS-B JSON data to CSV format."""
    convert_json_to_csv(input, output)

@adsb.command(name="filter")
@click.option('-i', '--input', required=True, help='Input CSV file path')
@click.option('--lat', type=float, required=True, help='Reference latitude')
@click.option('--lon', type=float, required=True, help='Reference longitude')
@click.option('--radius', type=float, required=True, help='Search radius in kilometers')
@click.option('-o', '--output', required=True, help='Filtered CSV output file')
@click.option('--tracks-dir', default='tracks', help='Directory for individual track files')
def filter_adsb(input, lat, lon, radius, output, tracks_dir):
    """Filter tracks based on a geographic area."""
    filter_tracks(
        input_csv_path=input,
        filtered_csv_path=output,
        tracks_folder=tracks_dir,
        ref_lat=lat,
        ref_lon=lon,
        ref_range_m=radius * 1000  # Convert km to meters
    )

@adsb.command(name="tracks2json")
@click.option('-i', '--input', required=True, help='Tracks folder path (filtered CSV files)')
@click.option('-o', '--output', required=True, help='Output folder for trajectory JSON files')
def tracks_to_json(input, output):
    """Convert filtered track CSV files to trajectory JSON files."""
    convert_tracks_to_json(input, output)

# ------------------ Visualization Commands ------------------
@cli.group()
def vis():
    """Visualization commands."""
    pass

@vis.command(name="visualize")
@click.option('-i', '--input-folder', required=True, help='Folder containing CSV/JSON track files')
@click.option('-o', '--output-file', required=True, help='Output file (HTML for folium or KML for KML)')
@click.option('--method', type=click.Choice(['folium', 'kml']), default='folium',
              help='Visualization method (default: folium)')
def visualize(input_folder, output_file, method):
    """Generate a combined visualization from track files."""
    visualize_folder(input_folder, output_file, method=method)

# ------------------ Tracks from Google Earth Commands ------------------
@cli.group()
def tracks():
    """Commands for processing tracks from Google Earth."""
    pass

@tracks.command(name="kml2csv")
@click.option('-i', '--input-kml', required=True, help='Input KML file path')
@click.option('-o', '--output-csv', required=True, help='Output CSV file path')
@click.option('--interval', type=int, default=10, help='Time interval in seconds between track points')
def kml_to_csv(input_kml, output_csv, interval):
    """Convert a KML file of tracks to CSV format."""
    from aerosim_utils.tracks_from_map import parse_kml, generate_csv_from_tracks
    tracks_data = parse_kml(input_kml)
    if not tracks_data:
        click.echo("No tracks found in the KML file.")
        return
    generate_csv_from_tracks(tracks_data, output_csv, interval_seconds=interval)

# ------------------ Scenario Generation Commands ------------------
@cli.group()
def scenario():
    """Scenario generation commands."""
    pass

@scenario.command(name="generate")
@click.option('-t', '--trajectories-folder', default="trajectories", help="Folder with trajectory JSON files")
@click.option('-o', '--output-file', default="auto_gen_scenario.json", help="Output scenario JSON file")
def generate_scenario(trajectories_folder, output_file):
    """Generate simulation scenario JSON from trajectory files."""
    generate_scenario_json(trajectories_folder, output_file)

# ------------------ Artificial Track Generation Commands ------------------
@cli.group()
def artificial():
    """Commands for generating artificial tracks."""
    pass

@artificial.command(name="generate-tracks")
@click.option('--num-tracks', type=int, required=True, help='Number of artificial tracks to generate')
@click.option('--maneuver', type=click.Choice(['random', 'circular', 'elliptical', 'flyby', 'square', 'rectangle', 'zigzag', 'spiral']),
              default='random', help='Track maneuver type')
@click.option('--center-lat', type=float, required=True, help='Center latitude')
@click.option('--center-lon', type=float, required=True, help='Center longitude')
@click.option('--center-alt', type=float, required=True, help='Center altitude in meters')
@click.option('--separation', type=float, default=0.005, help='Separation distance in degrees')
@click.option('--time-delay', type=int, default=30, help='Time delay (seconds) between tracks')
@click.option('--num-points', type=int, default=10, help='Number of points per track')
@click.option('--interval', type=int, default=10, help='Time interval (seconds) between points')
@click.option('-o', '--output', required=True, help='Output CSV file for artificial tracks')
@click.option('--fly-along', is_flag=True, help='Enable fly-along mode')
@click.option('--ownship-file', type=str, help='Path to ownship trajectory file (for fly-along mode)')
@click.option('--ownship-format', type=click.Choice(['json', 'csv']), default='json', help='Ownship trajectory file format')
def generate_tracks(num_tracks, maneuver, center_lat, center_lon, center_alt, separation, time_delay,
                    num_points, interval, output, fly_along, ownship_file, ownship_format):
    """Generate artificial tracks and save them to a CSV file."""
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
        fly_along=fly_along,
        ownship_trajectory_file=ownship_file,
        ownship_format=ownship_format,
        num_points=num_points,
        interval_seconds=interval
    )
    generator.generate()
    generator.save_to_csv(output)

# ------------------ Workflow Commands ------------------
@cli.group()
def workflow():
    """Commands to run complete processing workflows."""
    pass

@cli.group()
def report():
    """Commands for generating reports and visualizations."""
    pass

@report.command(name="scenario")
@click.option('-i', '--input', required=True, help='Input scenario JSON file path')
@click.option('-o', '--output', default='scenario_report.md', help='Output markdown report file path')
@click.option('--plot', is_flag=True, help='Generate trajectory plot')
@click.option('--plot-output', default='trajectories.png', help='Output plot file path')
def generate_scenario_report(input, output, plot, plot_output):
    """Generate a markdown report and optional trajectory plot from a scenario JSON file."""
    from aerosim_utils.scenario_report import generate_markdown_report, save_markdown_report, plot_trajectories
    import json
    
    with open(input, 'r', encoding='utf-8') as f:
        scenario = json.load(f)
    
    # Generate and save the markdown report
    report_md = generate_markdown_report(scenario)
    save_markdown_report(report_md, output)
    
    # Generate trajectory plot if requested
    if plot:
        plot_trajectories(scenario, plot_output)

@workflow.command(name="openadsb")
@click.option('--input-json', type=str, help='Input ADS-B JSON file path (optional)')
@click.option('--lat', type=float, default=34.217411, help='Reference latitude')
@click.option('--lon', type=float, default=-118.491081, help='Reference longitude')
@click.option('--radius', type=float, default=50, help='Search radius in kilometers')
@click.option('--interval', type=int, default=10, help='Time interval (seconds) between points')
def openadsb(input_json, lat, lon, radius, interval):
    """Run the complete ADS-B processing workflow."""
    scenario_data = process_openadsb_workflow(
        input_json=input_json,
        center_lat=lat,
        center_lon=lon,
        radius_km=radius,
        interval=interval
    )
    click.echo("ADS-B workflow completed. Scenario JSON:")
    click.echo(json.dumps(scenario_data, indent=4))

@workflow.command(name="artificial")
@click.option('--num-tracks', type=int, default=3, help='Number of artificial tracks')
@click.option('--maneuver', type=click.Choice(['random', 'circular', 'elliptical', 'flyby', 'square', 'rectangle', 'zigzag', 'spiral']),
              default='random', help='Track maneuver type')
@click.option('--center-lat', type=float, default=34.217411, help='Center latitude')
@click.option('--center-lon', type=float, default=-118.491081, help='Center longitude')
@click.option('--center-alt', type=float, default=1000, help='Center altitude in meters')
@click.option('--separation', type=float, default=0.005, help='Separation distance in degrees')
@click.option('--time-delay', type=int, default=30, help='Time delay between tracks (seconds)')
@click.option('--num-points', type=int, default=20, help='Number of points per track')
@click.option('--interval', type=int, default=10, help='Time interval between points (seconds)')
def artificial(num_tracks, maneuver, center_lat, center_lon, center_alt, separation, time_delay,
               num_points, interval):
    """Run the complete artificial track workflow."""
    scenario_data = process_artificial_workflow(
        maneuver=maneuver,
        num_tracks=num_tracks,
        center_lat=center_lat,
        center_lon=center_lon,
        center_alt=center_alt,
        separation=separation,
        time_delay=time_delay,
        num_points=num_points,
        interval_seconds=interval
    )
    click.echo("Artificial track workflow completed. Scenario JSON:")
    click.echo(json.dumps(scenario_data, indent=4))

@workflow.command(name="kml")
@click.option('--input-kml', type=str, required=True, help='Input KML file path')
@click.option('--interval', type=int, default=10, help='Time interval between points (seconds)')
def kml(input_kml, interval):
    """Run the complete Google Earth KML workflow."""
    scenario_data = process_kml_workflow(input_kml, interval=interval)
    click.echo("KML workflow completed. Scenario JSON:")
    click.echo(json.dumps(scenario_data, indent=4))

if __name__ == '__main__':
    cli()
