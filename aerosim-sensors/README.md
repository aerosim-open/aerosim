# aerosim-sensors

AeroSim Sensors for the AeroSim Simulator. This repository contains the sensor models and related functionalities for the AeroSim simulation environment.

## GNSS Sensor Module

This module implements a GNSS (Global Navigation Satellite System) sensor, which can be used to perform various geospatial calculations, including coordinate translation, distance calculation, and coordinate transformations between different systems (like Mercator and ECEF).

- **GNSS Structure**: The `GNSS` struct represents a GNSS sensor with longitude, latitude, and altitude properties.
- **Coordinate Transformations**:
  - **Mercator Projection**: Convert geographical coordinates to and from the Mercator projection.
  - **ECEF (Earth-Centered, Earth-Fixed) Coordinates**: Convert geographical coordinates to ECEF coordinates and vice versa.
  - **NED (North-East-Down) System**: Transform ECEF coordinates to NED coordinates relative to a reference point.
- **Distance Calculation**: Calculate the distance between two GNSS points using the Vincenty formula, which accounts for the Earth's flattening.
- **Coordinate Translation**: Translate the GNSS point in the x, y, and z directions, effectively moving the point by a given distance in the local coordinate system.
