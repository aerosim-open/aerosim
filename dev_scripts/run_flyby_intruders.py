from aerosim import AeroSim
from aerosim_core import lla_to_ned

import math
import numpy as np

import json


# -------------------------------------------------------------------------------------
# Function: Calculate spherical arc distance and bearing between two LLAs
# -------------------------------------------------------------------------------------
def distance_m_bearing_deg(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    """
    * @brief Calculate spherical arc distance and bearing between two LLAs (Haversine)
    *
    * @param lat1_deg Origin Latitude in degree
    * @param lon1_deg Origin Longitude in degree
    * @param lat2_deg Destination Latitude in degree
    * @param lon2_deg Destination Longitude in degree
    * @return pair<double,double> Distance in meters, bearing in degree
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
    R = 6372800.0  # For Earth radius in kilometers use 6372.8 km;

    # Calculate bearing
    bearing = math.atan2(
        math.sin(dLon) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dLon),
    )
    bearing *= 180.0 / math.pi
    if bearing < 0:
        bearing += 360.0

    # Return distance in meters
    return R * c, bearing


# -------------------------------------------------------------------------------------
# Function: Set evtol vehicle mission waypoints
# -------------------------------------------------------------------------------------
def set_world_origin(initial_lla, origin_altitude_m, config_filepath):
    # Read original scenario file
    sim_config_json = []
    with open(config_filepath, "r") as file:
        sim_config_json = json.load(file)

    # Set world original
    sim_config_json["world"]["origin"]["latitude"] = initial_lla[0]
    sim_config_json["world"]["origin"]["longitude"] = initial_lla[1]
    sim_config_json["world"]["origin"]["altitude"] = origin_altitude_m
    with open(config_filepath, "w") as file:
        json.dump(sim_config_json, file, indent=4)


# -------------------------------------------------------------------------------------
# Function: Set evtol vehicle mission waypoints
# -------------------------------------------------------------------------------------
def set_evtol_vehicle_mission_waypoints(
    vehicle_idx, mission_waypoints, initial_lla, config_filepath
):
    # Constants
    KTS2MPS = 0.514444  # Knots to meters per second
    R = 6372800.0  # For Earth radius in meters
    DEG2FT = 60.0 * 6076.0  # Degree to feet
    FT2M = 0.3048  # Feet to meter

    # Create waypoint structure for evtol_vehicle_fmu mask parameter waypoints
    # [North_m, East_m, Down_m, Heading_deg, Gama_deg, Wypt_Speed_m/s, Wypt_Capture_Distance_m, Start_Speed_Capture_Distance_Befor_Arrival_m, Speed_Capture_Duration_Distance_m]
    evtol_fmu_waypoints = np.zeros((100, 9))

    # Calculate initial heading (initial heading is calculated between first and third waypoint)
    _, initial_hdg_deg = distance_m_bearing_deg(
        mission_waypoints[0][0],
        mission_waypoints[0][1],
        mission_waypoints[2][0],
        mission_waypoints[2][1],
    )

    # Convert mission waypoints to eVTOL FMU waypoints
    for idx in range(len(mission_waypoints)):
        # Convert LLA to NED
        evtol_fmu_waypoints[idx][:3] = lla_to_ned(
            mission_waypoints[idx][0],
            mission_waypoints[idx][1],
            mission_waypoints[idx][2],
            initial_lla[0],
            initial_lla[1],
            initial_lla[2],
        )
        evtol_fmu_waypoints[idx][0] = round(evtol_fmu_waypoints[idx][0], 3)
        evtol_fmu_waypoints[idx][1] = round(evtol_fmu_waypoints[idx][1], 3)
        evtol_fmu_waypoints[idx][2] = round(evtol_fmu_waypoints[idx][2], 3)

        # Calculate waypoint heading(deg)
        if idx == 0:
            evtol_fmu_waypoints[idx][3] = round(initial_hdg_deg, 1)
        else:
            distance_m, bearing_deg = distance_m_bearing_deg(
                mission_waypoints[idx - 1][0],
                mission_waypoints[idx - 1][1],
                mission_waypoints[idx][0],
                mission_waypoints[idx][1],
            )
            if distance_m == 0:
                evtol_fmu_waypoints[idx][3] = round(evtol_fmu_waypoints[idx - 1][3], 1)
            else:
                evtol_fmu_waypoints[idx][3] = round(bearing_deg, 1)

        # Calculate waypoint gamma (deg)
        if idx == 0:
            evtol_fmu_waypoints[idx][4] = 0.0
        else:
            rise_m = mission_waypoints[idx][2] - mission_waypoints[idx - 1][2]
            curvature_adj_m = R * (
                1 - math.cos(distance_m / DEG2FT / FT2M * math.pi / 180.0)
            )
            evtol_fmu_waypoints[idx][4] = round(
                math.degrees(math.atan2(rise_m + curvature_adj_m, distance_m)), 1
            )

        # Set Wypt_Speed_m/s and Wypt_Capture_Distance_m
        evtol_fmu_waypoints[idx][5] = mission_waypoints[idx][3]  # Wypt_Speed_m/s
        evtol_fmu_waypoints[idx][6] = mission_waypoints[idx][
            4
        ]  # Wypt_Capture_Distance_m

        # Calculate Start_Speed_Capture_Distance_Befor_Arrival_m
        if math.sin(evtol_fmu_waypoints[idx][4]) == 0:
            evtol_fmu_waypoints[idx][7] = mission_waypoints[idx][
                5
            ]  # Start_Speed_Capture_Distance_Befor_Arrival_m
        else:
            # Adjust for slant range due to automatically calculated gamma waypoint frame
            evtol_fmu_waypoints[idx][7] = round(
                mission_waypoints[idx][5]
                / math.cos(math.radians(evtol_fmu_waypoints[idx][4])),
                1,
            )

        # Set Speed_Capture_Duration_Distance_m
        evtol_fmu_waypoints[idx][8] = mission_waypoints[idx][
            6
        ]  # Speed_Capture_Duration_Distance_m

    # Read original scenario file
    sim_config_json = []
    with open(config_filepath, "r") as file:
        sim_config_json = json.load(file)

    # Modify vehicle initial orientation
    sim_config_json["world"]["actors"][vehicle_idx]["transform"]["rotation"] = [
        0.0,
        0.0,
        round(initial_hdg_deg, 1),
    ]

    # Setup evtol_vehicle_fmu mask parameter
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"][
        "init_wypt_num"
    ] = 1.0
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"]["init_ned_m"] = [
        evtol_fmu_waypoints[0][0],
        evtol_fmu_waypoints[0][1],
        evtol_fmu_waypoints[0][2],
    ]
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"]["init_rpy_rad"] = [
        0.0,
        0.0,
        round(math.radians(initial_hdg_deg), 6),
    ]
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"]["num_waypoints"] = (
        float(len(mission_waypoints))
    )
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"][
        "waypoints"
    ] = evtol_fmu_waypoints.T.flatten().tolist()
    with open(config_filepath, "w") as file:
        json.dump(sim_config_json, file, indent=4)


# -------------------------------------------------------------------------------------
# Setup eVTOL vehicle mission waypoints
# -------------------------------------------------------------------------------------
# Configurations
ORIGIN_ALTITUDE_M = 260.5  # Initial altitude at origin
config_filepath = "config/sim_config_flyby_intruders.json"

# Read ownship mission waypoints
# [Latitude_deg, Longitude_deg, Altitude_m, Wypt_Speed_m/s, Wypt_Capture_Distance_m, Start_Speed_Capture_Distance_Befor_Arrival_m, Speed_Capture_Duration_Distance_m]
ownship_mission_waypoints = np.genfromtxt(
    "mission_waypoints/mission_waypoint_flyby_intruders.txt", delimiter=","
)

# Set world original
initial_lla = [
    ownship_mission_waypoints[0][0],
    ownship_mission_waypoints[0][1],
    ownship_mission_waypoints[0][2],
]
set_world_origin(initial_lla, ORIGIN_ALTITUDE_M, config_filepath)

# Set ownship eVTOL vehicle mission waypoints
set_evtol_vehicle_mission_waypoints(
    0, ownship_mission_waypoints, initial_lla, config_filepath
)


# -------------------------------------------------------------------------------------
# Run AeroSim simulation
# -------------------------------------------------------------------------------------
aerosim = AeroSim()
aerosim.run(config_filepath)

try:
    input("Simulation is running. Press any key to stop...")
except KeyboardInterrupt:
    print("Simulation stopped.")
finally:
    # --------------------------------------------
    # Stop AeroSim simulation
    # --------------------------------------------
    aerosim.stop()
