#!/usr/bin/env python3
"""
Utils module for simulation tools.

This module provides various utility functions including:
- Conversion between geodetic (LLA) and ECEF coordinates.
- Conversion between ECEF and NED coordinates.
- LLA to NED conversion and its inverse (NED to LLA).
- Processing CSV files with waypoints to compute NED coordinates.
- Distance calculations using the Haversine formula and 3D Euclidean metric.
- Bearing (forward azimuth) calculation between two points.
"""

import numpy as np
import pandas as pd

# WGS84 ellipsoid constants
A = 6378137.0                # semi-major axis in meters
E_SQ = 6.69437999014e-3        # first eccentricity squared

def geodetic_to_ecef(lat, lon, alt):
    """
    Convert geodetic coordinates (latitude, longitude, altitude) to ECEF.
    
    Parameters:
        lat (float): Latitude in degrees.
        lon (float): Longitude in degrees.
        alt (float): Altitude in meters.
    
    Returns:
        tuple: (x, y, z) in meters.
    """
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    N = A / np.sqrt(1 - E_SQ * np.sin(lat_rad)**2)
    x = (N + alt) * np.cos(lat_rad) * np.cos(lon_rad)
    y = (N + alt) * np.cos(lat_rad) * np.sin(lon_rad)
    z = (N * (1 - E_SQ) + alt) * np.sin(lat_rad)
    return x, y, z

def ecef_to_geodetic(x, y, z):
    """
    Convert ECEF coordinates (x, y, z) to geodetic coordinates.
    
    Parameters:
        x (float): ECEF x-coordinate in meters.
        y (float): ECEF y-coordinate in meters.
        z (float): ECEF z-coordinate in meters.
    
    Returns:
        tuple: (latitude in degrees, longitude in degrees, altitude in meters).
    """
    lon = np.arctan2(y, x)
    p = np.sqrt(x*x + y*y)
    lat = np.arctan2(z, p * (1 - E_SQ))  # initial guess
    alt = 0
    # Iterative improvement (5 iterations usually suffice)
    for _ in range(5):
        N = A / np.sqrt(1 - E_SQ * np.sin(lat)**2)
        alt = p / np.cos(lat) - N
        lat = np.arctan2(z + E_SQ * N * np.sin(lat), p)
    return np.degrees(lat), np.degrees(lon), alt

def ecef_to_ned(dx, dy, dz, ref_lat, ref_lon):
    """
    Convert differences in ECEF coordinates (dx, dy, dz) to NED coordinates.
    
    Parameters:
        dx, dy, dz (float): Differences in ECEF coordinates (meters).
        ref_lat (float): Reference latitude in degrees.
        ref_lon (float): Reference longitude in degrees.
    
    Returns:
        tuple: (north, east, down) in meters.
    """
    lat_rad = np.radians(ref_lat)
    lon_rad = np.radians(ref_lon)
    north = -np.sin(lat_rad)*np.cos(lon_rad)*dx - np.sin(lat_rad)*np.sin(lon_rad)*dy + np.cos(lat_rad)*dz
    east  = -np.sin(lon_rad)*dx + np.cos(lon_rad)*dy
    down  = -np.cos(lat_rad)*np.cos(lon_rad)*dx - np.cos(lat_rad)*np.sin(lon_rad)*dy - np.sin(lat_rad)*dz
    return north, east, down

def ned_to_ecef(north, east, down, ref_lat, ref_lon):
    """
    Convert NED coordinates (north, east, down) to differences in ECEF coordinates (dx, dy, dz).
    
    Parameters:
        north, east, down (float): NED coordinates in meters.
        ref_lat (float): Reference latitude in degrees.
        ref_lon (float): Reference longitude in degrees.
    
    Returns:
        tuple: (dx, dy, dz) in meters.
    """
    lat_rad = np.radians(ref_lat)
    lon_rad = np.radians(ref_lon)
    # Inverse of the rotation matrix (transpose) is used here.
    dx = -np.sin(lat_rad)*np.cos(lon_rad)*north - np.sin(lon_rad)*east - np.cos(lat_rad)*np.cos(lon_rad)*down
    dy = -np.sin(lat_rad)*np.sin(lon_rad)*north + np.cos(lon_rad)*east - np.cos(lat_rad)*np.sin(lon_rad)*down
    dz = np.cos(lat_rad)*north - np.sin(lat_rad)*down
    return dx, dy, dz

def lla_to_ned(lat, lon, alt, ref_lat, ref_lon, ref_alt):
    """
    Convert a single LLA point to NED coordinates relative to a reference LLA point.
    
    Parameters:
        lat, lon, alt (float): Target point in LLA (degrees, degrees, meters).
        ref_lat, ref_lon, ref_alt (float): Reference point in LLA (degrees, degrees, meters).
    
    Returns:
        tuple: (north, east, down) in meters.
    """
    target_x, target_y, target_z = geodetic_to_ecef(lat, lon, alt)
    ref_x, ref_y, ref_z = geodetic_to_ecef(ref_lat, ref_lon, ref_alt)
    dx = target_x - ref_x
    dy = target_y - ref_y
    dz = target_z - ref_z
    return ecef_to_ned(dx, dy, dz, ref_lat, ref_lon)

def ned_to_lla(north, east, down, ref_lat, ref_lon, ref_alt):
    """
    Convert a single NED point relative to a reference LLA point back to LLA coordinates.
    
    Parameters:
        north, east, down (float): NED coordinates in meters.
        ref_lat, ref_lon, ref_alt (float): Reference LLA point (degrees, degrees, meters).
    
    Returns:
        tuple: (latitude in degrees, longitude in degrees, altitude in meters).
    """
    ref_x, ref_y, ref_z = geodetic_to_ecef(ref_lat, ref_lon, ref_alt)
    dx, dy, dz = ned_to_ecef(north, east, down, ref_lat, ref_lon)
    x = ref_x + dx
    y = ref_y + dy
    z = ref_z + dz
    return ecef_to_geodetic(x, y, z)

def process_trajectory(input_file, output_file, ref_lat=None, ref_lon=None, ref_alt=None):
    """
    Process a CSV file of LLA waypoints, compute and append NED coordinates, then save the result.
    
    If no reference point is provided, the first waypoint in the CSV is used.
    
    Parameters:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to save the output CSV file.
        ref_lat, ref_lon, ref_alt (float, optional): Reference LLA point.
    """
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    cols_lower = [str(col).strip().lower() for col in df.columns]
    lat_idx, lon_idx, alt_idx = None, None, None
    for i, col in enumerate(cols_lower):
        if "lat" in col and lat_idx is None:
            lat_idx = i
        elif ("lon" in col or "long" in col) and lon_idx is None:
            lon_idx = i
        elif "alt" in col and alt_idx is None:
            alt_idx = i
    if lat_idx is None or lon_idx is None or alt_idx is None:
        lat_series = df[df.columns[0]]
        lon_series = df[df.columns[1]]
        alt_series = df[df.columns[2]]
    else:
        lat_series = df[df.columns[lat_idx]]
        lon_series = df[df.columns[lon_idx]]
        alt_series = df[df.columns[alt_idx]]
    
    if ref_lat is None or ref_lon is None or ref_alt is None:
        ref_lat = lat_series.iloc[0]
        ref_lon = lon_series.iloc[0]
        ref_alt = alt_series.iloc[0]
        print(f"No reference point provided. Using first waypoint as reference: ({ref_lat}, {ref_lon}, {ref_alt})")
    
    ref_x, ref_y, ref_z = geodetic_to_ecef(ref_lat, ref_lon, ref_alt)
    north_list, east_list, down_list = [], [], []
    
    for i in range(len(df)):
        lat = lat_series.iloc[i]
        lon = lon_series.iloc[i]
        alt = alt_series.iloc[i]
        x, y, z = geodetic_to_ecef(lat, lon, alt)
        dx = x - ref_x
        dy = y - ref_y
        dz = z - ref_z
        north, east, down = ecef_to_ned(dx, dy, dz, ref_lat, ref_lon)
        north_list.append(north)
        east_list.append(east)
        down_list.append(down)
    
    df['north'] = north_list
    df['east'] = east_list
    df['down'] = down_list
    
    if output_file is None:
        output_file = "ned_output.csv"
    
    df.to_csv(output_file, index=False)
    print(f"NED coordinates saved to {output_file}")

def process_single_point(lat, lon, alt, ref_lat, ref_lon, ref_alt, output_file=None):
    """
    Process a single LLA point to compute its NED coordinates relative to a reference point.
    
    Parameters:
        lat, lon, alt (float): Target point in LLA (degrees, degrees, meters).
        ref_lat, ref_lon, ref_alt (float): Reference LLA point (degrees, degrees, meters).
        output_file (str, optional): If provided, the result is saved to this CSV file.
    """
    north, east, down = lla_to_ned(lat, lon, alt, ref_lat, ref_lon, ref_alt)
    print("Single point conversion:")
    print(f"Input LLA: ({lat}, {lon}, {alt})")
    print(f"Reference LLA: ({ref_lat}, {ref_lon}, {ref_alt})")
    print(f"NED: North = {north:.3f} m, East = {east:.3f} m, Down = {down:.3f} m")
    
    if output_file is not None:
        data = {
            "lat": [lat],
            "lon": [lon],
            "alt": [alt],
            "north": [north],
            "east": [east],
            "down": [down]
        }
        result_df = pd.DataFrame(data)
        result_df.to_csv(output_file, index=False)
        print(f"Result saved to {output_file}")

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth's surface using the Haversine formula.
    
    Parameters:
        lat1, lon1 (float): Latitude and longitude of the first point (in degrees).
        lat2, lon2 (float): Latitude and longitude of the second point (in degrees).
    
    Returns:
        float: Distance in meters.
    """
    R = A  # Using the WGS84 semi-major axis as an approximation for Earth's radius.
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a_val = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c_val = 2 * np.arctan2(np.sqrt(a_val), np.sqrt(1 - a_val))
    distance = R * c_val
    return distance

def euclidean_distance_lla(lat1, lon1, alt1, lat2, lon2, alt2):
    """
    Calculate the 3D Euclidean distance between two LLA points by converting them to ECEF.
    
    Parameters:
        lat1, lon1, alt1 (float): First point (degrees, degrees, meters).
        lat2, lon2, alt2 (float): Second point (degrees, degrees, meters).
    
    Returns:
        float: Distance in meters.
    """
    x1, y1, z1 = geodetic_to_ecef(lat1, lon1, alt1)
    x2, y2, z2 = geodetic_to_ecef(lat2, lon2, alt2)
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def bearing_between_points(lat1, lon1, lat2, lon2):
    """
    Calculate the initial bearing (forward azimuth) from point 1 to point 2.
    
    Parameters:
        lat1, lon1 (float): Latitude and longitude of the first point (in degrees).
        lat2, lon2 (float): Latitude and longitude of the second point (in degrees).
    
    Returns:
        float: Bearing in degrees (0° = north).
    """
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlon = lon2_rad - lon1_rad
    x = np.sin(dlon) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
    bearing_rad = np.arctan2(x, y)
    bearing_deg = (np.degrees(bearing_rad) + 360) % 360
    return bearing_deg

if __name__ == "__main__":
    # Example usage: LLA to NED conversion
    lat, lon, alt = 37.7749, -122.4194, 10   # Example: San Francisco (approx.)
    ref_lat, ref_lon, ref_alt = 37.7749, -122.4194, 0  # Using same lat/lon, different altitude as reference
    print("LLA to NED conversion example:")
    north, east, down = lla_to_ned(lat, lon, alt, ref_lat, ref_lon, ref_alt)
    print(f"NED: North = {north:.3f} m, East = {east:.3f} m, Down = {down:.3f} m")
    
    # Example usage: Distance calculations between San Francisco and Los Angeles
    lat2, lon2, alt2 = 34.0522, -118.2437, 15  # Example: Los Angeles (approx.)
    haversine_dist = haversine_distance(lat, lon, lat2, lon2)
    euclidean_dist = euclidean_distance_lla(lat, lon, alt, lat2, lon2, alt2)
    print(f"Haversine distance: {haversine_dist/1000:.3f} km")
    print(f"3D Euclidean distance: {euclidean_dist/1000:.3f} km")
    
    # Example usage: Bearing calculation
    bearing = bearing_between_points(lat, lon, lat2, lon2)
    print(f"Initial bearing from San Francisco to Los Angeles: {bearing:.3f}°")
