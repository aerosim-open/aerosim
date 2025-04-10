import json
import os
import sys

def generate_markdown_report(scenario):
    lines = []
    lines.append("# Simulation Scenario Report")
    lines.append("")
    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"**Description:** {scenario.get('description', 'No description provided.')}")
    lines.append("")
    
    # Clock
    clock = scenario.get("clock", {})
    lines.append("## Clock Settings")
    lines.append("")
    lines.append(f"- **Step Size (ms):** {clock.get('step_size_ms', 'N/A')}")
    lines.append(f"- **Pace 1x Scale:** {clock.get('pace_1x_scale', 'N/A')}")
    lines.append("")
    
    # Orchestrator
    orch = scenario.get("orchestrator", {})
    lines.append("## Orchestrator")
    lines.append("")
    sync_topics = orch.get("sync_topics", [])
    lines.append("- **Sync Topics:**")
    for topic in sync_topics:
        lines.append(f"  - **Topic:** `{topic.get('topic', 'N/A')}`, **Interval (ms):** {topic.get('interval_ms', 'N/A')}")
    lines.append(f"- **Output Data File:** `{orch.get('output_sim_data_file', 'N/A')}`")
    lines.append("")
    
    # World Settings
    world = scenario.get("world", {})
    lines.append("## World Settings")
    lines.append("")
    lines.append(f"- **Update Interval (ms):** {world.get('update_interval_ms', 'N/A')}")
    origin = world.get("origin", {})
    lines.append("- **Origin:**")
    lines.append(f"  - **Latitude:** {origin.get('latitude', 'N/A')}")
    lines.append(f"  - **Longitude:** {origin.get('longitude', 'N/A')}")
    lines.append(f"  - **Altitude:** {origin.get('altitude', 'N/A')}")
    weather = world.get("weather", {})
    lines.append(f"- **Weather Preset:** {weather.get('preset', 'N/A')}")
    lines.append("")
    
    # Actors
    actors = world.get("actors", [])
    lines.append("## Actors")
    lines.append("")
    if actors:
        for actor in actors:
            lines.append(f"### Actor: {actor.get('actor_name', 'Unnamed')}")
            lines.append(f"- **Asset:** {actor.get('actor_asset', 'N/A')}")
            lines.append(f"- **Description:** {actor.get('description', 'No description')}")
            transform = actor.get("transform", {})
            lines.append(f"- **Position:** {transform.get('position', 'N/A')}")
            state = actor.get("state", {})
            lines.append(f"- **State Topic:** `{state.get('topic', 'N/A')}`")
            effectors = actor.get("effectors", [])
            if effectors:
                lines.append("- **Effectors:**")
                for eff in effectors:
                    lines.append(f"  - **ID:** `{eff.get('id', 'N/A')}`, **State Topic:** `{eff.get('state', {}).get('topic', 'N/A')}`")
            flight_deck = actor.get("flight_deck", [])
            if flight_deck:
                lines.append("- **Flight Deck:**")
                for fd in flight_deck:
                    lines.append(f"  - **ID:** `{fd.get('id', 'N/A')}`, **State Topic:** `{fd.get('state', {}).get('topic', 'N/A')}`")
            lines.append("")
    else:
        lines.append("No actors defined.")
    lines.append("")
    
    # Sensors
    sensors = world.get("sensors", [])
    lines.append("## Sensors")
    lines.append("")
    if sensors:
        for sensor in sensors:
            lines.append(f"### Sensor: {sensor.get('sensor_name', 'Unnamed')}")
            lines.append(f"- **Type:** {sensor.get('type', 'N/A')}")
            lines.append(f"- **Parent Actor:** {sensor.get('parent', 'N/A')}")
            transform = sensor.get("transform", {})
            lines.append(f"- **Translation:** {transform.get('translation', 'N/A')}")
            parameters = sensor.get("parameters", {})
            lines.append("- **Parameters:**")
            lines.append(f"  - **Resolution:** {parameters.get('resolution', 'N/A')}")
            lines.append(f"  - **Frame Rate:** {parameters.get('frame_rate', 'N/A')} fps")
            lines.append(f"  - **Field of View:** {parameters.get('fov', 'N/A')}°")
            lines.append(f"  - **Capture Enabled:** {parameters.get('capture_enabled', 'N/A')}")
            lines.append("")
    else:
        lines.append("No sensors defined.")
    lines.append("")
    
    # Renderers
    renderers = scenario.get("renderers", [])
    lines.append("## Renderers")
    lines.append("")
    if renderers:
        for renderer in renderers:
            lines.append(f"### Renderer ID: {renderer.get('renderer_id', 'N/A')}")
            lines.append(f"- **Role:** {renderer.get('role', 'N/A')}")
            sensors_used = renderer.get("sensors", [])
            lines.append(f"- **Sensors:** {', '.join(sensors_used) if sensors_used else 'None'}")
            active_camera = renderer.get("viewport_config", {}).get("active_camera", "N/A")
            lines.append(f"- **Active Camera:** {active_camera}")
            lines.append("")
    else:
        lines.append("No renderers defined.")
    lines.append("")
    
    # FMU Models
    fmu_models = scenario.get("fmu_models", [])
    lines.append("## FMU Models")
    lines.append("")
    if fmu_models:
        for fmu in fmu_models:
            lines.append(f"### FMU: {fmu.get('id', 'Unnamed')}")
            lines.append(f"- **FMU Model Path:** {fmu.get('fmu_model_path', 'N/A')}")
            inputs = fmu.get("component_input_topics", [])
            outputs = fmu.get("component_output_topics", [])
            if inputs:
                lines.append("- **Input Topics:**")
                for inp in inputs:
                    lines.append(f"  - `{inp.get('topic', 'N/A')}` (Msg Type: {inp.get('msg_type', 'N/A')})")
            if outputs:
                lines.append("- **Output Topics:**")
                for out in outputs:
                    lines.append(f"  - `{out.get('topic', 'N/A')}` (Msg Type: {out.get('msg_type', 'N/A')})")
            
            # Waypoints file if exists
            fmu_init = fmu.get("fmu_initial_vals", {})
            waypoints = fmu_init.get("waypoints_json_path")
            if waypoints:
                lines.append(f"- **Waypoints File:** `{waypoints}`")
            lines.append("")
    else:
        lines.append("No FMU models defined.")
    lines.append("")
    
    lines.append("---")
    lines.append("This report was auto-generated from the scenario JSON file.")
    return "\n".join(lines)


def save_markdown_report(md_text, filename="scenario_report.md"):
    with open(filename, "w", encoding="utf-8") as md_file:
        md_file.write(md_text)
    print(f"Markdown report saved as {filename}")


def plot_trajectories(scenario, output_filename="trajectories.png"):
    """
    For each FMU model that contains a 'waypoints_json_path' in its 'fmu_initial_vals',
    read the trajectory data and plot the trajectories on a 5x5 mile map.
    The trajectory JSON is expected to be a list of dicts with keys: 'time', 'lat', 'lon', 'alt'.
    """
    try:
        import matplotlib.pyplot as plt
        import geopandas as gpd
        from shapely.geometry import LineString
        import contextily as ctx
    except ImportError:
        print("Error: To plot trajectories, please install: geopandas, contextily, shapely, matplotlib")
        return

    fmu_models = scenario.get("fmu_models", [])
    trajectories = []
    labels = []
    
    for fmu in fmu_models:
        init_vals = fmu.get("fmu_initial_vals", {})
        waypoints_path = init_vals.get("waypoints_json_path")
        if waypoints_path and os.path.exists(waypoints_path):
            with open(waypoints_path, "r", encoding="utf-8") as wf:
                wp_data = json.load(wf)
            # Create a list of (lon, lat) tuples from the waypoints
            coords = [(point["lon"], point["lat"]) for point in wp_data if "lon" in point and "lat" in point]
            if coords:
                trajectories.append(LineString(coords))
                labels.append(fmu.get("id", "unknown"))
    
    if not trajectories:
        print("No trajectories found to plot.")
        return
    
    # Create a GeoDataFrame using the trajectories as the geometry column
    gdf = gpd.GeoDataFrame({"label": labels}, geometry=trajectories, crs="EPSG:4326")
    # Convert to Web Mercator for basemap compatibility
    gdf = gdf.to_crs(epsg=3857)
    
    # Set a fixed square extent (5 miles x 5 miles).
    # 5 miles is roughly 8046.72 meters.
    square_size = 8046.72  # meters
    half_square = square_size / 2
    
    # Get the center of the trajectories' bounding box
    minx, miny, maxx, maxy = gdf.total_bounds
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    fig, ax = plt.subplots(figsize=(10, 10))
    # Plot each trajectory with a label
    for idx, row in gdf.iterrows():
        gdf.iloc[[idx]].plot(ax=ax, linewidth=2, label=row["label"])
    
    # Set the map extent to be a square of 5 miles (8046.72 m) centered at the calculated center
    ax.set_xlim(center_x - half_square, center_x + half_square)
    ax.set_ylim(center_y - half_square, center_y + half_square)
    
    ax.set_axis_off()
    # Use OpenStreetMap's Mapnik provider as the basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    
    plt.legend()
    plt.title("Trajectories of Vehicles (5x5 Mile Map)")
    plt.savefig(output_filename, bbox_inches="tight")
    plt.close()
    print(f"Trajectories plot saved as {output_filename}")


def main():
    # Determine the scenario JSON file from command-line (or default to scenario.json)
    if len(sys.argv) > 1:
        json_filename = sys.argv[1]
    else:
        json_filename = "test.json"
    
    if not os.path.exists(json_filename):
        print(f"ERROR: File '{json_filename}' not found!")
        sys.exit(1)
    
    with open(json_filename, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    
    # Generate and save the Markdown report
    report_md = generate_markdown_report(scenario)
    save_markdown_report(report_md)
    
    # Generate and save the trajectories visualization (fixed 5x5 mile map)
    plot_trajectories(scenario)


if __name__ == '__main__':
    main()
