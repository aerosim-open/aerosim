#!/usr/bin/env python3
import click
import json
import os
import sys
import subprocess
from pathlib import Path
from utils import (
    convert_json_to_csv,
    filter_tracks,
    convert_tracks_to_json,
    visualize_folder,
    generate_scenario_json,
    ArtificialTrackGenerator,
    process_openadsb_workflow,
    process_artificial_workflow,
    process_kml_workflow,
    clamp,
    normalize_heading_deg,
    distance_m_bearing_deg,
    scenario_report
)
from utils.config import Config

def handle_error(func):
    """Decorator to handle common errors in CLI commands."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            click.echo(f"Error: File not found - {str(e)}", err=True)
            sys.exit(1)
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON - {str(e)}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)
    return wrapper

def get_aerosim_root(ctx, param, value):
    """Get Aerosim root directory from environment or path argument."""
    if value:
        return value
    aerosim_root = os.environ.get('AEROSIM_ROOT')
    if not aerosim_root:
        raise click.BadParameter("AEROSIM_ROOT environment variable not set and no path provided")
    return aerosim_root

@click.group()
def cli():
    """Aerosim Utils - Tools for trajectory conversion, visualization, scenario generation, and track generation."""
    pass

# ------------------ Installation and Build Commands ------------------
@cli.group()
def prereqs():
    """Commands for installing prerequisites."""
    pass

@prereqs.command(name="install")
@click.option('--platform', type=click.Choice(['windows', 'linux']), default=None,
              help='Platform to install prerequisites for (default: current platform)')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def install_prereqs(platform, path):
    """Install prerequisites for Aerosim."""
    if platform is None:
        platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"pre_install.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Pre-install script not found at {script_path}", err=True)
        sys.exit(1)
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)], check=True)
        else:
            subprocess.run(['bash', str(script_path)], check=True)
        click.echo("Prerequisites installed successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error installing prerequisites: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def install():
    """Commands for installing Aerosim components."""
    pass

@install.command(name="all")
@click.option('--platform', type=click.Choice(['windows', 'linux']), default=None,
              help='Platform to install for (default: current platform)')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def install_all(platform, path):
    """Install all Aerosim components."""
    if platform is None:
        platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"install_aerosim.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Install script not found at {script_path}", err=True)
        sys.exit(1)
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)], check=True)
        else:
            subprocess.run(['bash', str(script_path)], check=True)
        click.echo("Aerosim installed successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error installing Aerosim: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def build():
    """Commands for building Aerosim."""
    pass

@build.command(name="all")
@click.option('--platform', type=click.Choice(['windows', 'linux']), default=None,
              help='Platform to build for (default: current platform)')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def build_all(platform, path):
    """Build all Aerosim components."""
    if platform is None:
        platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"build_aerosim.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Build script not found at {script_path}", err=True)
        sys.exit(1)
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)], check=True)
        else:
            subprocess.run(['bash', str(script_path)], check=True)
        click.echo("Aerosim built successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error building Aerosim: {str(e)}", err=True)
        sys.exit(1)

@build.command(name="wheels")
@click.option('--platform', type=click.Choice(['windows', 'linux']), default=None,
              help='Platform to build wheels for (default: current platform)')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def build_wheels(platform, path):
    """Build Python wheels for Aerosim."""
    if platform is None:
        platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"build_wheels.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Build wheels script not found at {script_path}", err=True)
        sys.exit(1)
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)], check=True)
        else:
            subprocess.run(['bash', str(script_path)], check=True)
        click.echo("Aerosim wheels built successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error building Aerosim wheels: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def launch():
    """Commands for launching Aerosim."""
    pass

@launch.command(name="unreal")
@click.option('--editor/--no-editor', default=False, help='Launch in editor mode')
@click.option('--nogui/--gui', default=False, help='Launch without GUI')
@click.option('--pixel-streaming/--no-pixel-streaming', default=False, help='Enable pixel streaming')
@click.option('--pixel-streaming-ip', default='127.0.0.1', help='Pixel streaming IP address')
@click.option('--pixel-streaming-port', default=8888, help='Pixel streaming port')
@click.option('--config', type=click.Choice(['Debug', 'Development', 'Shipping']), default='Development',
              help='Build configuration')
@click.option('--renderer-ids', default='0', help='Comma-separated list of renderer IDs')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def launch_unreal(editor, nogui, pixel_streaming, pixel_streaming_ip, pixel_streaming_port, config, renderer_ids, path):
    """Launch Aerosim with Unreal Engine."""
    platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"launch_aerosim.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Launch script not found at {script_path}", err=True)
        sys.exit(1)
    
    args = []
    if editor:
        args.append('--unreal-editor')
    elif nogui:
        args.append('--unreal-editor-nogui')
    else:
        args.append('--unreal')
    
    if pixel_streaming:
        args.append('--pixel-streaming')
        args.extend(['--pixel-streaming-ip', pixel_streaming_ip])
        args.extend(['--pixel-streaming-port', str(pixel_streaming_port)])
    
    args.extend(['--config', config])
    args.extend(['--renderer-ids', renderer_ids])
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)] + args, check=True)
        else:
            subprocess.run(['bash', str(script_path)] + args, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error launching Aerosim: {str(e)}", err=True)
        sys.exit(1)

@launch.command(name="omniverse")
@click.option('--pixel-streaming/--no-pixel-streaming', default=False, help='Enable pixel streaming')
@click.option('--path', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              callback=get_aerosim_root, help='Path to Aerosim root directory')
@handle_error
def launch_omniverse(pixel_streaming, path):
    """Launch Aerosim with Omniverse."""
    platform = 'windows' if os.name == 'nt' else 'linux'
    
    script_path = Path(path) / f"launch_aerosim.{'bat' if platform == 'windows' else 'sh'}"
    if not script_path.exists():
        click.echo(f"Error: Launch script not found at {script_path}", err=True)
        sys.exit(1)
    
    args = ['--omniverse']
    if pixel_streaming:
        args.append('--pixel-streaming')
    
    try:
        if platform == 'windows':
            subprocess.run([str(script_path)] + args, check=True)
        else:
            subprocess.run(['bash', str(script_path)] + args, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error launching Aerosim: {str(e)}", err=True)
        sys.exit(1)

# ------------------ Configuration Commands ------------------
@cli.group()
def config():
    """Configuration management commands."""
    pass

@config.command(name="show")
def show_config():
    """Show current configuration."""
    click.echo(json.dumps(Config._config, indent=4))

@config.command(name="set")
@click.argument('key')
@click.argument('value')
def set_config(key, value):
    """Set a configuration value."""
    try:
        # Try to convert value to appropriate type
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        elif value.replace('.', '', 1).isdigit():
            value = float(value)
        elif value.startswith('[') and value.endswith(']'):
            value = json.loads(value)
        
        Config.set(key, value)
        click.echo(f"Set {key} = {value}")
    except Exception as e:
        click.echo(f"Error setting configuration: {str(e)}", err=True)
        sys.exit(1)

@config.command(name="reset")
def reset_config():
    """Reset configuration to defaults."""
    Config.reset()
    click.echo("Configuration reset to defaults")

@config.command(name="validate")
def validate_config():
    """Validate current configuration."""
    if Config.validate_config():
        click.echo("Configuration is valid")
    else:
        click.echo("Configuration validation failed", err=True)
        sys.exit(1)

# ------------------ ADS-B Data Commands ------------------
@cli.group()
def adsb():
    """Commands for processing ADS-B data."""
    pass

@adsb.command(name="json2csv")
@click.option('-i', '--input', required=True, help='Input ADS-B JSON file path')
@click.option('-o', '--output', required=True, help='Output CSV file path')
@handle_error
def json_to_csv(input, output):
    """Convert ADS-B JSON data to CSV format."""
    convert_json_to_csv(input, output)
    click.echo(f"Successfully converted {input} to {output}")

@adsb.command(name="filter")
@click.option('-i', '--input', required=True, help='Input CSV file path')
@click.option('--lat', type=float, default=Config.get('DEFAULT_CENTER_LAT'), help='Reference latitude')
@click.option('--lon', type=float, default=Config.get('DEFAULT_CENTER_LON'), help='Reference longitude')
@click.option('--radius', type=float, default=Config.get('DEFAULT_RADIUS_KM'), help='Search radius in kilometers')
@click.option('-o', '--output', required=True, help='Filtered CSV output file')
@click.option('--tracks-dir', default=Config.get('DEFAULT_TRACKS_DIR'), help='Directory for individual track files')
@handle_error
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
    click.echo(f"Successfully filtered tracks from {input} to {output}")

@adsb.command(name="tracks2json")
@click.option('-i', '--input', required=True, help='Tracks folder path (filtered CSV files)')
@click.option('-o', '--output', required=True, help='Output folder for trajectory JSON files')
@handle_error
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
@handle_error
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
@handle_error
def kml_to_csv(input_kml, output_csv, interval):
    """Convert a KML file of tracks to CSV format."""
    from utils.tracks_from_map import parse_kml, generate_csv_from_tracks
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
@handle_error
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
@handle_error
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
@click.option('-i', '--input', required=True, type=click.Path(exists=True), help='Input scenario JSON file path')
@click.option('-o', '--output', type=click.Path(), default='reports/scenario_report.md', help='Output markdown report file path')
@click.option('--plot/--no-plot', default=True, help='Generate trajectory plot')
@click.option('--plot-output', type=click.Path(), default='reports/trajectories.png', help='Output plot file path')
@handle_error
def generate_scenario_report(input, output, plot, plot_output):
    """Generate a markdown report and optional trajectory plot from a scenario JSON file."""
    with open(input, 'r', encoding='utf-8') as f:
        scenario = json.load(f)
    
    # Generate and save the markdown report
    report_md = scenario_report.generate_markdown_report(scenario)
    scenario_report.save_markdown_report(report_md, output)
    click.echo(f"Scenario report saved to {output}")
    
    # Generate trajectory plot if requested
    if plot:
        scenario_report.plot_trajectories(scenario, plot_output)
        click.echo(f"Trajectory plot saved to {plot_output}")

@workflow.command(name="openadsb")
@click.option('--input-json', type=str, help='Input ADS-B JSON file path (optional)')
@click.option('--lat', type=float, default=34.217411, help='Reference latitude')
@click.option('--lon', type=float, default=-118.491081, help='Reference longitude')
@click.option('--radius', type=float, default=50, help='Search radius in kilometers')
@click.option('--interval', type=int, default=10, help='Time interval (seconds) between points')
@click.option('--generate-report/--no-report', default=True, help='Generate a markdown report after workflow completion')
@click.option('--report-output', type=click.Path(), default='reports/scenario_report.md', help='Output markdown report file path')
@click.option('--plot-trajectories/--no-plot', default=True, help='Generate trajectory plot')
@click.option('--plot-output', type=click.Path(), default='reports/trajectories.png', help='Output plot file path')
@handle_error
def openadsb(input_json, lat, lon, radius, interval, generate_report, report_output, plot_trajectories, plot_output):
    """Run the complete ADS-B processing workflow."""
    scenario_data = process_openadsb_workflow(
        input_json=Path(input_json) if input_json else None,
        center_lat=lat,
        center_lon=lon,
        radius_km=radius,
        interval=interval,
        generate_report=generate_report,
        report_output=Path(report_output),
        plot_trajectories=plot_trajectories,
        plot_output=Path(plot_output)
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
@click.option('--generate-report/--no-report', default=True, help='Generate a markdown report after workflow completion')
@click.option('--report-output', type=click.Path(), default='reports/scenario_report_artificial.md', help='Output markdown report file path')
@click.option('--plot-trajectories/--no-plot', default=True, help='Generate trajectory plot')
@click.option('--plot-output', type=click.Path(), default='reports/trajectories_artificial.png', help='Output plot file path')
@handle_error
def artificial(num_tracks, maneuver, center_lat, center_lon, center_alt, separation, time_delay,
               num_points, interval, generate_report, report_output, plot_trajectories, plot_output):
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
        interval_seconds=interval,
        generate_report=generate_report,
        report_output=Path(report_output),
        plot_trajectories=plot_trajectories,
        plot_output=Path(plot_output)
    )
    click.echo("Artificial track workflow completed. Scenario JSON:")
    click.echo(json.dumps(scenario_data, indent=4))

@workflow.command(name="kml")
@click.option('--input-kml', type=str, required=True, help='Input KML file path')
@click.option('--interval', type=int, default=10, help='Time interval between points (seconds)')
@click.option('--generate-report/--no-report', default=True, help='Generate a markdown report after workflow completion')
@click.option('--report-output', type=click.Path(), default='reports/scenario_report_kml.md', help='Output markdown report file path')
@click.option('--plot-trajectories/--no-plot', default=True, help='Generate trajectory plot')
@click.option('--plot-output', type=click.Path(), default='reports/trajectories_kml.png', help='Output plot file path')
@handle_error
def kml(input_kml, interval, generate_report, report_output, plot_trajectories, plot_output):
    """Run the complete Google Earth KML workflow."""
    scenario_data = process_kml_workflow(
        input_kml=Path(input_kml),
        interval=interval,
        generate_report=generate_report,
        report_output=Path(report_output),
        plot_trajectories=plot_trajectories,
        plot_output=Path(plot_output)
    )
    click.echo("KML workflow completed. Scenario JSON:")
    click.echo(json.dumps(scenario_data, indent=4))

@cli.group()
def helpers():
    """Helper utility functions."""
    pass

@helpers.command(name="clamp")
@click.option('--value', type=float, required=True, help='Value to clamp')
@click.option('--min', type=float, required=True, help='Minimum value')
@click.option('--max', type=float, required=True, help='Maximum value')
@handle_error
def clamp_value(value, min, max):
    """Clamp a value between minimum and maximum."""
    result = clamp(value, min, max)
    click.echo(f"Clamped value: {result}")

@helpers.command(name="normalize-heading")
@click.option('--heading', type=float, required=True, help='Heading in degrees')
@handle_error
def normalize_heading(heading):
    """Normalize a heading to the range [0, 360)."""
    result = normalize_heading_deg(heading)
    click.echo(f"Normalized heading: {result}")

@helpers.command(name="distance-bearing")
@click.option('--lat1', type=float, required=True, help='First point latitude')
@click.option('--lon1', type=float, required=True, help='First point longitude')
@click.option('--lat2', type=float, required=True, help='Second point latitude')
@click.option('--lon2', type=float, required=True, help='Second point longitude')
@handle_error
def calculate_distance_bearing(lat1, lon1, lat2, lon2):
    """Calculate distance and bearing between two points."""
    distance, bearing = distance_m_bearing_deg(lat1, lon1, lat2, lon2)
    click.echo(f"Distance: {distance:.2f} meters")
    click.echo(f"Bearing: {bearing:.2f} degrees")

if __name__ == '__main__':
    cli()
