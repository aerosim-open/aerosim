import os
import csv
import json
import random
from datetime import datetime

import pandas as pd
import folium
import matplotlib.colors as mcolors

###############################
# Data Loading and Normalization
###############################

def load_data_to_df(input_file, default_track_id=None):
    """
    Load data from a CSV or JSON file into a pandas DataFrame.
    
    For JSON files, if the keys "lat", "lon", "alt", and "time" exist,
    they are renamed to "latitude", "longitude", "altitude", and "timestamp"
    to match the CSV schema.
    
    If the "trackId" column is missing, a default value is assigned.
    By default, this value is taken as the name of the folder containing the file,
    or "trajectory" if no folder exists.
    
    Args:
        input_file (str): Path to the CSV or JSON file.
        default_track_id (str, optional): Default track ID to use if missing.
    
    Returns:
        pd.DataFrame: DataFrame with normalized column names.
    """
    _, ext = os.path.splitext(input_file)
    ext = ext.lower()
    if ext == '.csv':
        df = pd.read_csv(input_file)
    elif ext == '.json':
        try:
            df = pd.read_json(input_file)
        except ValueError:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
    else:
        raise ValueError("Unsupported file format. Only CSV and JSON are supported.")
    
    # Normalize column names for JSON trajectory files.
    if 'lat' in df.columns and 'lon' in df.columns:
        df.rename(columns={'lat': 'latitude', 'lon': 'longitude'}, inplace=True)
    if 'alt' in df.columns:
        df.rename(columns={'alt': 'altitude'}, inplace=True)
    if 'time' in df.columns:
        df.rename(columns={'time': 'timestamp'}, inplace=True)
    
    # Determine default_track_id from the folder name if not provided.
    if default_track_id is None:
        folder = os.path.dirname(input_file)
        if folder:
            default_track_id = os.path.basename(folder)
        else:
            default_track_id = "trajectory"
    
    # If there is no "trackId" column, add one using the default track ID.
    if 'trackId' not in df.columns:
        df['trackId'] = default_track_id
    
    return df

def combine_data_from_folder(input_folder):
    """
    Load and combine data from all CSV/JSON files in the specified folder into a single DataFrame.
    
    Args:
        input_folder (str): Directory containing CSV/JSON files.
        
    Returns:
        pd.DataFrame: Combined DataFrame (or an empty DataFrame if none found).
    """
    all_dfs = []
    for filename in os.listdir(input_folder):
        full_path = os.path.join(input_folder, filename)
        if os.path.isfile(full_path) and os.path.splitext(filename)[1].lower() in ['.csv', '.json']:
            try:
                df = load_data_to_df(full_path)
                all_dfs.append(df)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()

###############################
# Folium-based Visualization  #
###############################

def generate_tooltip(row):
    """
    Generate an HTML tooltip from a DataFrame row.
    
    Uses a detailed tooltip if expected keys (e.g., "eventName") exist;
    otherwise, produces a simplified version.
    """
    if 'eventName' in row:
        tooltip = (
            f"<b>Event Name:</b> {row['eventName']}<br>"
            f"<b>Track ID:</b> {row['trackId']}<br>"
            f"<b>Source ID:</b> {row['sourceId']}<br>"
            f"<b>Track Type:</b> {row['trackType']}<br>"
            f"<b>Timestamp:</b> {row['timestamp']}<br>"
            f"<b>Data:</b> {row['data']}<br>"
            f"<b>Altitude Reference:</b> {row['altitudeReference']}<br>"
            f"<b>Source Track ID:</b> {row['sourceTrackId']}<br>"
            f"<b>Longitude:</b> {row['longitude']}<br>"
            f"<b>Latitude:</b> {row['latitude']}<br>"
            f"<b>Altitude:</b> {row['altitude']}<br>"
            f"<b>AGL Altitude:</b> {row['aglAltitude']}<br>"
            f"<b>MSL Altitude:</b> {row['mslAltitude']}<br>"
            f"<b>WGS84 Altitude:</b> {row['wgs84Altitude']}"
        )
    else:
        tooltip = (
            f"<b>Timestamp:</b> {row['timestamp']}<br>"
            f"<b>Altitude:</b> {row.get('altitude', '')}"
        )
    return tooltip

def plot_tracks(input_file, output_html):
    """
    Plot track data from a single CSV or JSON file on an interactive folium map with tooltips.
    
    Args:
        input_file (str): Path to the CSV or JSON file.
        output_html (str): Path to save the generated HTML map.
    """
    df = load_data_to_df(input_file)
    _plot_df(df, output_html)

def _plot_df(df, output_html):
    """
    Internal helper to plot a DataFrame of track data onto a folium map.
    
    Args:
        df (pd.DataFrame): DataFrame containing track data.
        output_html (str): Path to save the generated HTML map.
    """
    if df.empty:
        print("No data to plot.")
        return
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    track_ids = df["trackId"].unique()
    color_list = list(mcolors.CSS4_COLORS.values())
    random.shuffle(color_list)

    for i, track_id in enumerate(track_ids):
        track_data = df[df["trackId"] == track_id].sort_values("timestamp")
        points = list(zip(track_data["latitude"], track_data["longitude"]))
        color = color_list[i % len(color_list)]
        if len(points) > 1:
            folium.PolyLine(points, color=color, weight=2.5, opacity=1).add_to(m)
        for idx, row in track_data.iterrows():
            tooltip_text = generate_tooltip(row)
            folium.CircleMarker(
                location=(row["latitude"], row["longitude"]),
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=tooltip_text
            ).add_to(m)
    m.save(output_html)
    print(f"Combined map with tooltips has been saved to {output_html}")

def plot_combined_tracks_from_folder(input_folder, output_html):
    """
    Combine all CSV/JSON files in a folder and plot the tracks on a single folium map.
    
    Args:
        input_folder (str): Directory containing CSV/JSON files.
        output_html (str): Path to save the generated HTML map.
    """
    combined_df = combine_data_from_folder(input_folder)
    if combined_df.empty:
        print("No valid data found in folder.")
        return
    _plot_df(combined_df, output_html)

###############################
# KML-based Visualization     #
###############################

def parse_csv(file_path):
    """
    Parse a CSV file and return a list of dictionaries.
    """
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def parse_json(file_path):
    """
    Parse a JSON file and return its content.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def unify_records(records, input_format):
    """
    Convert records into a unified format with keys:
      - track_id, timestamp, longitude, latitude, altitude
    """
    unified = []
    for idx, rec in enumerate(records):
        if input_format == 'csv':
            if 'timestamp' in rec and 'trackId' in rec and 'wgs84Altitude' in rec:
                track_id = rec.get('trackId', f'Point{idx}')
                timestamp = rec.get('timestamp', '')
                longitude = rec.get('longitude', '')
                latitude = rec.get('latitude', '')
                altitude = rec.get('wgs84Altitude', '')
            else:
                track_id = rec.get('trackId', f'Point{idx}')
                timestamp = rec.get('timestamp', '')
                longitude = rec.get('longitude', rec.get('lon', ''))
                latitude = rec.get('latitude', rec.get('lat', ''))
                altitude = rec.get('wgs84Altitude', rec.get('altitude', rec.get('alt', '0')))
        elif input_format == 'json':
            track_id = rec.get('trackId', 'trajectory')
            timestamp = rec.get('time', '')
            longitude = rec.get('lon', '')
            latitude = rec.get('lat', '')
            altitude = rec.get('alt', '')
        else:
            continue

        try:
            timestamp_val = float(timestamp)
        except:
            timestamp_val = timestamp
        try:
            longitude_val = float(longitude)
        except:
            longitude_val = 0.0
        try:
            latitude_val = float(latitude)
        except:
            latitude_val = 0.0
        try:
            altitude_val = float(altitude)
        except:
            altitude_val = 0.0

        unified.append({
            'track_id': track_id,
            'timestamp': timestamp_val,
            'longitude': longitude_val,
            'latitude': latitude_val,
            'altitude': altitude_val
        })
    return unified

def unify_dataframe(df):
    """
    Convert a DataFrame into a list of unified records with keys:
      - track_id, timestamp, longitude, latitude, altitude
    """
    records = []
    for idx, row in df.iterrows():
        try:
            timestamp_val = float(row['timestamp'])
        except:
            timestamp_val = row['timestamp']
        try:
            longitude_val = float(row['longitude'])
        except:
            longitude_val = 0.0
        try:
            latitude_val = float(row['latitude'])
        except:
            latitude_val = 0.0
        try:
            altitude_val = float(row['altitude'])
        except:
            altitude_val = 0.0
        record = {
            'track_id': row['trackId'],
            'timestamp': timestamp_val,
            'longitude': longitude_val,
            'latitude': latitude_val,
            'altitude': altitude_val
        }
        records.append(record)
    return records

def group_by_track(unified_records):
    groups = {}
    for rec in unified_records:
        tid = rec['track_id']
        groups.setdefault(tid, []).append(rec)
    for tid in groups:
        groups[tid] = sorted(groups[tid], key=lambda x: x['timestamp'])
    return groups

def get_color(index):
   
    colors = [
        "ff0000ff",  # Red
        "ff00ff00",  # Green
        "ffff0000",  # Blue
        "ff00ffff",  # Yellow
        "ffffff00",  # Cyan
        "ff990099",  # Purple
        "ff0099ff",  # Orange-ish
        "ff99ff00",  # Lime
    ]
    return colors[index % len(colors)]


def generate_styles(track_ids):
    styles = []
    for idx, tid in enumerate(sorted(track_ids)):
        color = get_color(idx)
        style = f"""
    <Style id="style_{tid}">
      <LineStyle>
        <color>{color}</color>
        <width>4</width>
      </LineStyle>
      <IconStyle>
        <color>{color}</color>
        <scale>1.2</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <scale>0</scale>
      </LabelStyle>
    </Style>
        """.strip()
        styles.append(style)
    return styles

def generate_trajectory_placemarks(groups):
    placemarks = []
    for tid, points in groups.items():
        coords = " ".join([f"{pt['longitude']},{pt['latitude']},{pt['altitude']}" for pt in points])
        placemark = f"""
    <Placemark>
        <name>{tid}</name>
        <styleUrl>#style_{tid}</styleUrl>
        <LineString>
            <extrude>1</extrude>
            <tessellate>1</tessellate>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>
                {coords}
            </coordinates>
        </LineString>
    </Placemark>
        """.strip()
        placemarks.append(placemark)
    return placemarks

def generate_marker_placemarks(groups):
    markers = []
    for tid, points in groups.items():
        for pt in points:
            placemark = f"""
    <Placemark>
        <name>{tid}</name>
        <styleUrl>#style_{tid}</styleUrl>
        <description>Timestamp: {pt['timestamp']}</description>
        <Point>
            <coordinates>{pt['longitude']},{pt['latitude']},{pt['altitude']}</coordinates>
        </Point>
    </Placemark>
            """.strip()
            markers.append(placemark)
    return markers

def create_kml(styles, trajectory_placemarks, marker_placemarks):
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>3D Trajectories with Markers</name>
    {''.join(styles)}
    {''.join(trajectory_placemarks)}
    {''.join(marker_placemarks)}
</Document>
</kml>"""
    return kml_content

def convert_waypoints_to_kml(input_file, output_file=None, input_format=None):
    if input_format is None:
        _, ext = os.path.splitext(input_file)
        ext = ext.lower()
        if ext == '.json':
            input_format = 'json'
        elif ext == '.csv':
            input_format = 'csv'
        else:
            raise ValueError("Could not determine input format. Please specify input_format='csv' or 'json'.")
    
    if input_format == 'csv':
        records = parse_csv(input_file)
    elif input_format == 'json':
        records = parse_json(input_file)
    else:
        raise ValueError("Invalid input_format specified.")
    
    unified_records = unify_records(records, input_format)
    groups = group_by_track(unified_records)
    styles = generate_styles(groups.keys())
    trajectory_placemarks = generate_trajectory_placemarks(groups)
    marker_placemarks = generate_marker_placemarks(groups)
    kml_content = create_kml(styles, trajectory_placemarks, marker_placemarks)
    
    if output_file is None:
        base, _ = os.path.splitext(input_file)
        output_file = base + '.kml'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)
    print(f"KML file successfully created at: {output_file}")

def convert_combined_tracks_to_kml(input_folder, output_file):
    """
    Combine all CSV/JSON files in a folder and generate a single KML file.
    
    Args:
        input_folder (str): Directory containing CSV/JSON files.
        output_file (str): Path to save the combined KML file.
    """
    combined_df = combine_data_from_folder(input_folder)
    if combined_df.empty:
        print("No valid data found in folder.")
        return
    records = unify_dataframe(combined_df)
    groups = group_by_track(records)
    styles = generate_styles(groups.keys())
    trajectory_placemarks = generate_trajectory_placemarks(groups)
    marker_placemarks = generate_marker_placemarks(groups)
    kml_content = create_kml(styles, trajectory_placemarks, marker_placemarks)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)
    print(f"Combined KML file successfully created at: {output_file}")

###############################
# Folder-Level Visualization (Combined)
###############################

def visualize_folder(input_folder, output_file, method='folium'):
    """
    Combine all files in a folder and generate a single visualization file.
    
    Args:
        input_folder (str): Directory containing input files (CSV/JSON).
        output_file (str): Output file path (HTML for folium, KML for KML).
        method (str): 'folium' or 'kml'. Defaults to 'folium'.
    """
    if method == 'folium':
        plot_combined_tracks_from_folder(input_folder, output_file)
    elif method == 'kml':
        convert_combined_tracks_to_kml(input_folder, output_file)
    else:
        print(f"Unsupported visualization method: {method}")

if __name__ == "__main__":
    # Example usage:
    
    # 1. Visualize a single CSV or JSON file using folium.
    # plot_tracks("output.csv", "map_output.html")
    # plot_tracks("trajectories.json", "trajectory_map.html")
    
    # 2. Convert a single CSV (or JSON) file to KML.
    # convert_waypoints_to_kml("filteredoutput.csv", "filteredoutput.kml")
    
    # 3. Visualize all files in a folder as a combined map.
    # For folium (single HTML map):
    # visualize_folder("tracks", "combined_tracks_map.html", method='folium')
    # For KML (single KML file):
    # visualize_folder("trajectories", "combined_trajectories.kml", method='kml')
    
    pass
