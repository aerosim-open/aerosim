#!/usr/bin/env python3
"""
This script reads a KML file containing track data (from Google Earth),
extracts each track’s coordinates and associated metadata, and converts
them into a CSV file (kml_output.csv) that follows the expected simulator format.
"""

import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re

# Expected CSV columns
FIELDNAMES = [
    "eventName", "trackId", "sourceId", "trackType", "timestamp", "data",
    "altitudeReference", "sourceTrackId", "longitude", "latitude",
    "altitude", "aglAltitude", "mslAltitude", "wgs84Altitude"
]

def extract_track_id(name_text):
    """
    Extracts a numeric track ID from the Placemark name.
    For example, if the name is "Trajectory 10000", returns 10000.
    If no numeric ID is found, returns None.
    """
    match = re.search(r'\d+', name_text)
    if match:
        return int(match.group())
    return None

def parse_kml(kml_file):
    """
    Parse the KML file and return a dictionary where keys are track IDs
    and values are lists of coordinate tuples (lon, lat, alt).
    Assumes each Placemark contains a LineString with a <coordinates> element.
    """
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    tree = ET.parse(kml_file)
    root = tree.getroot()
    
    tracks = {}
    for placemark in root.findall(".//kml:Placemark", ns):
        name_elem = placemark.find("kml:name", ns)
        if name_elem is not None:
            name_text = name_elem.text
            track_id = extract_track_id(name_text)
        else:
            track_id = None
        # If no track_id found, assign a default value (e.g., 99999)
        if track_id is None:
            track_id = 99999

        # Get the coordinates from the LineString element
        coord_elem = placemark.find(".//kml:LineString/kml:coordinates", ns)
        if coord_elem is None:
            continue
        coord_text = coord_elem.text.strip()
        # Coordinates in KML are typically a space-separated list: "lon,lat,alt lon,lat,alt ..."
        coord_list = []
        for line in coord_text.split():
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    alt = float(parts[2])
                    coord_list.append((lon, lat, alt))
                except ValueError:
                    continue
        tracks[track_id] = coord_list
    return tracks

def generate_csv_from_tracks(tracks, output_csv, interval_seconds=10):
    """
    Generate a CSV file (output_csv) from the given tracks dictionary.
    Each track point is written as one row.
    """
    base_time = datetime.now(timezone.utc)
    rows = []
    for track_id, coordinates in tracks.items():
        # Use a fixed source for KML-converted tracks
        source_id = "GOOGLE_EARTH"
        track_type = "Surveillance"
        altitude_reference = "MSL"
        # Build sourceTrackId from source and track id.
        source_track_id = f"{source_id}::{track_id:05d}"
        # For each point, generate a row with a timestamp that increments by interval_seconds.
        for i, (lon, lat, alt) in enumerate(coordinates):
            timestamp = (base_time + timedelta(seconds=i * interval_seconds)).isoformat() + "Z"
            row = {
                "eventName": "track.appended",
                "trackId": f"{track_id:05d}",
                "sourceId": source_id,
                "trackType": track_type,
                "timestamp": timestamp,
                "data": "KML_TRACK",  # Placeholder data field
                "altitudeReference": altitude_reference,
                "sourceTrackId": source_track_id,
                "longitude": lon,
                "latitude": lat,
                "altitude": alt,
                "aglAltitude": alt * 0.35,  # Example computation for AGL altitude
                "mslAltitude": alt,
                "wgs84Altitude": alt - 50  # Example offset for WGS84 altitude
            }
            rows.append(row)
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"KML data converted and saved to '{output_csv}'")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert a KML file of tracks to CSV format for simulator use.")
    parser.add_argument("input_kml", help="Input KML file containing track data.")
    parser.add_argument("-o", "--output_csv", default="kml_output.csv",
                        help="Output CSV file (default: kml_output.csv)")
    parser.add_argument("--interval", type=int, default=10,
                        help="Time interval in seconds between track points (default: 10)")
    args = parser.parse_args()

    tracks = parse_kml(args.input_kml)
    if not tracks:
        print("No tracks found in the KML file.")
        return
    generate_csv_from_tracks(tracks, args.output_csv, interval_seconds=args.interval)

if __name__ == "__main__":
    main()
