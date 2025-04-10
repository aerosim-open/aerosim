import math
import csv
import json
import random
from datetime import datetime
from collections import defaultdict

def parse_timestamp(ts_str):
    """
    Parse an ISO8601 timestamp that may or may not include timezone information.
    
    Examples:
      "2024-07-25T18:21:11.337Z" or "2024-07-25T18:23:18.35Z"
    
    If timezone info is missing, the time is assumed to be in UTC.
    """
    from datetime import timezone
    is_utc = False
    # Remove trailing 'Z' and note that time is in UTC.
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1]
        is_utc = True
    # Attempt to remove colon from timezone offset if present.
    if ("+" in ts_str or "-" in ts_str[19:]):
        pos_plus = ts_str.rfind("+")
        pos_minus = ts_str.rfind("-")
        pos = max(pos_plus, pos_minus)
        if pos != -1:
            tz_part = ts_str[pos:]
            tz_part = tz_part.replace(":", "")
            ts_str = ts_str[:pos] + tz_part
    # First, try parsing with timezone (%z)
    try:
        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        # Fallback: try parsing without timezone
        dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
        if is_utc:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt


def convert_json_to_csv(input_json_path, output_csv_path):
    """
    Convert raw JSON data into a flattened CSV file.
    
    Args:
        input_json_path (str): Path to the input JSON file.
        output_csv_path (str): Path to save the CSV file.
    """
    with open(input_json_path, 'r') as json_file:
        data = json.load(json_file)

    rows = []
    for item in data:
        # Get event-level info
        event_name = item.get("eventName")
        track = item.get("surveillanceTrack", {})

        # Extract track details
        row = {
            "eventName": event_name,
            "trackId": track.get("trackId"),
            "sourceId": track.get("sourceId"),
            "trackType": track.get("trackType"),
            "timestamp": track.get("timestamp"),
            "data": track.get("data"),
            "altitudeReference": track.get("altitudeReference"),
            "sourceTrackId": track.get("sourceTrackId")
        }
        # Extract nested reference location
        ref_loc = track.get("referenceLocation", {})
        row.update({
            "longitude": ref_loc.get("longitude"),
            "latitude": ref_loc.get("latitude"),
            "altitude": ref_loc.get("altitude"),
            "aglAltitude": ref_loc.get("aglAltitude"),
            "mslAltitude": ref_loc.get("mslAltitude"),
            "wgs84Altitude": ref_loc.get("wgs84Altitude")
        })
        rows.append(row)

    fieldnames = [
        "eventName", "trackId", "sourceId", "trackType", "timestamp", "data",
        "altitudeReference", "sourceTrackId", "longitude", "latitude",
        "altitude", "aglAltitude", "mslAltitude", "wgs84Altitude"
    ]

    with open(output_csv_path, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV file has been created as '{output_csv_path}'.")

def filter_tracks(input_csv_path: str, 
                  filtered_csv_path: str, 
                  tracks_folder: str,
                  ref_lat: float, 
                  ref_lon: float, 
                  ref_range_m: float = 10000) -> None:
    """
    Filter track data based on distance from a reference point and group by track.

    Args:
        input_csv_path (str): Path to the input CSV file.
        filtered_csv_path (str): Path for the overall filtered CSV file.
        tracks_folder (str): Directory where individual track CSV files will be saved.
        ref_lat (float): Reference latitude.
        ref_lon (float): Reference longitude.
        ref_range_m (float, optional): Maximum allowed distance in meters. Defaults to 10000.
    """
    import pandas as pd
    import geopy.distance

    df = pd.read_csv(input_csv_path)
    df = df.dropna(subset=['latitude', 'longitude'])
    
    ref_coords = (ref_lat, ref_lon)
    
    def calculate_distance(row: pd.Series) -> float:
        point_coords = (row['latitude'], row['longitude'])
        return geopy.distance.geodesic(ref_coords, point_coords).meters

    df['distance_m'] = df.apply(calculate_distance, axis=1)
    filtered_df = df[df['distance_m'] < ref_range_m]
    filtered_df.to_csv(filtered_csv_path, index=False)
    print(f"Filtered data saved to '{filtered_csv_path}'")
    
    import os
    os.makedirs(tracks_folder, exist_ok=True)
    for track_id, group in filtered_df.groupby("trackId"):
        # Format track ID as a 5-digit number
        try:
            tid = int(float(track_id))
        except ValueError:
            tid = track_id
        track_path = os.path.join(tracks_folder, f"track_{tid:05d}.csv")
        group.to_csv(track_path, index=False)
        print(f"Track {track_id} data saved to '{track_path}'")

def process_csv(csv_path):
    """
    Process a CSV file of ADS-B track data:
      - Group rows by trackId.
      - Compute relative timestamps (starting at zero for each track).
      - Return a dict mapping trackId to trajectory list.
    """
    tracks = defaultdict(list)
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            track_id = row["trackId"]
            try:
                ts = parse_timestamp(row["timestamp"])
            except ValueError as e:
                print(f"Error parsing timestamp {row['timestamp']}: {e}")
                continue
            row["parsed_ts"] = ts
            tracks[track_id].append(row)
    trajectories = {}
    for track_id, rows in tracks.items():
        rows.sort(key=lambda x: x["parsed_ts"])
        base_ts = rows[0]["parsed_ts"]
        trajectory = []
        for row in rows:
            delta = (row["parsed_ts"] - base_ts).total_seconds()
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            try:
                height = float(row["mslAltitude"])
            except (ValueError, TypeError):
                height = float(row["altitude"])
            trajectory.append({
                "time": delta,
                "lat": lat,
                "lon": lon,
                "alt": height
            })
        trajectories[track_id] = trajectory
    return trajectories

def convert_tracks_to_json(input_folder, output_folder):
    """
    Convert all CSV track files in input_folder to Aerosim trajectory JSON files.
    
    Args:
        input_folder (str): Directory containing CSV track files.
        output_folder (str): Directory where trajectory JSON files will be saved.
    """
    import os
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".csv"):
            csv_path = os.path.join(input_folder, filename)
            trajectories = process_csv(csv_path)
            for track_id, trajectory in trajectories.items():
                try:
                    track_num = int(float(track_id))
                except ValueError:
                    track_num = track_id
                output_filename = os.path.join(output_folder, f"{track_num:05d}_trajectory.json")
                with open(output_filename, "w") as jsonfile:
                    json.dump(trajectory, jsonfile, indent=2)
                print(f"Saved trajectory for track {track_id} to {output_filename}")
