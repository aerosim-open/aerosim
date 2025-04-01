"""
Helper functions for AeroSim.

This module provides common utility functions used throughout the AeroSim package.
"""

import math
from typing import Tuple


def clamp(n: float, minn: float, maxn: float) -> float:
    """
    Clamp a value between a minimum and maximum value.

    Args:
        n: Value to clamp
        minn: Minimum allowed value
        maxn: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min(maxn, n), minn)


def normalize_heading_deg(heading: float) -> float:
    """
    Normalize a heading value to the range [0, 360).

    Args:
        heading: Heading in degrees

    Returns:
        Normalized heading in degrees
    """
    while heading < 0.0:
        heading += 360.0
    while heading >= 360.0:
        heading -= 360.0
    return heading


def distance_m_bearing_deg(lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float) -> Tuple[float, float]:
    """
    Calculate spherical arc distance and bearing between two LLAs (Haversine).

    Args:
        lat1_deg: Origin Latitude in degrees
        lon1_deg: Origin Longitude in degrees
        lat2_deg: Destination Latitude in degrees
        lon2_deg: Destination Longitude in degrees

    Returns:
        Tuple of (distance in meters, bearing in degrees)
    """
    # Convert degree to radian
    lat1 = lat1_deg * math.pi / 180.0
    lon1 = lon1_deg * math.pi / 180.0
    lat2 = lat2_deg * math.pi / 180.0
    lon2 = lon2_deg * math.pi / 180.0

    # Calculate difference between latitudes and longitudes
    dLat = lat2 - lat1
    dLon = lon2 - lon1

    # Haversine formula
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(lat1) * math.cos(
        lat2
    ) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.asin(math.sqrt(a))
    R = 6372800.0  # For Earth radius in meters

    # Calculate bearing
    bearing = math.atan2(
        math.sin(dLon) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dLon),
    )
    bearing *= 180.0 / math.pi
    if bearing < 0:
        bearing += 360.0

    # Return distance in meters and bearing in degrees
    return R * c, bearing
