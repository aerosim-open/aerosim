from aerosim import AeroSim
from aerosim_core import lla_to_ned
from aerosim_data import types as aerosim_types
from aerosim_data import middleware

import math
import numpy as np
import json


# -------------------------------------------------------------------------------------
# Function: Calculate spherical arc distance and bearing between two LLAs
# -------------------------------------------------------------------------------------
def distance_m_bearing_deg(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    """
    Calculate spherical arc distance and bearing between two LLAs using the Haversine formula.

    @param lat1_deg: Origin latitude in degrees.
    @param lon1_deg: Origin longitude in degrees.
    @param lat2_deg: Destination latitude in degrees.
    @param lon2_deg: Destination longitude in degrees.
    @return: Tuple (distance in meters, bearing in degrees)
    """
    # Convert degrees to radians
    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    lat2 = math.radians(lat2_deg)
    lon2 = math.radians(lon2_deg)

    dLat = lat2 - lat1
    dLon = lon2 - lon1

    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    R = 6372800.0  # Earth radius in meters

    # Calculate bearing
    bearing = math.atan2(
        math.sin(dLon) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dLon),
    )
    bearing = math.degrees(bearing)
    if bearing < 0:
        bearing += 360.0

    return R * c, bearing


# -------------------------------------------------------------------------------------
# Function: Set world origin in the simulation configuration file
# -------------------------------------------------------------------------------------
def set_world_origin(initial_lla, origin_altitude_m, config_filepath):
    """
    Update the simulation configuration file with the world origin.

    @param initial_lla: List or tuple [latitude, longitude, altitude] for the origin.
    @param origin_altitude_m: Altitude (in meters) at the origin.
    @param config_filepath: Path to the simulation configuration file.
    """
    with open(config_filepath, "r") as file:
        sim_config_json = json.load(file)

    sim_config_json["world"]["origin"]["latitude"] = initial_lla[0]
    sim_config_json["world"]["origin"]["longitude"] = initial_lla[1]
    sim_config_json["world"]["origin"]["altitude"] = origin_altitude_m

    with open(config_filepath, "w") as file:
        json.dump(sim_config_json, file, indent=4)


# -------------------------------------------------------------------------------------
# Function: Set eVTOL vehicle mission waypoints for a given vehicle index
# -------------------------------------------------------------------------------------
def set_evtol_vehicle_mission_waypoints(
    vehicle_idx, mission_waypoints, initial_lla, config_filepath
):
    """
    Convert mission waypoints from LLA to NED coordinates and update the configuration file
    for a specific vehicle.

    @param vehicle_idx: Index of the vehicle in the config file (0 for ownship, 1 for intruder).
    @param mission_waypoints: numpy array of mission waypoints, where each row is
                              [Latitude_deg, Longitude_deg, Altitude_m, Wypt_Speed_m/s,
                               Wypt_Capture_Distance_m, Start_Speed_Capture_Distance_Befor_Arrival_m,
                               Speed_Capture_Duration_Distance_m].
    @param initial_lla: Initial LLA used as the reference for NED conversion.
    @param config_filepath: Path to the simulation configuration file.
    """
    KTS2MPS = 0.514444  # Knots to meters per second
    R = 6372800.0  # Earth radius in meters
    DEG2FT = 60.0 * 6076.0  # Degree to feet conversion factor
    FT2M = 0.3048  # Feet to meters conversion

    # Create waypoint structure for evtol_vehicle_fmu mask parameter waypoints
    # [North_m, East_m, Down_m, Heading_deg, Gama_deg, Wypt_Speed_m/s, Wypt_Capture_Distance_m, Start_Speed_Capture_Distance_Befor_Arrival_m, Speed_Capture_Duration_Distance_m]
    evtol_fmu_waypoints = np.zeros((100, 9))

    # Calculate an initial heading (using the first and third waypoint)
    _, initial_hdg_deg = distance_m_bearing_deg(
        mission_waypoints[0][0],
        mission_waypoints[0][1],
        mission_waypoints[2][0],
        mission_waypoints[2][1],
    )

    for idx in range(len(mission_waypoints)):
        # Convert LLA to NED coordinates relative to the initial LLA
        evtol_fmu_waypoints[idx][:3] = lla_to_ned(
            mission_waypoints[idx][0],
            mission_waypoints[idx][1],
            mission_waypoints[idx][2],
            initial_lla[0],
            initial_lla[1],
            initial_lla[2],
        )
        # Calculate waypoint heading (deg)
        if idx == 0:
            evtol_fmu_waypoints[idx][3] = initial_hdg_deg
        else:
            distance_m, bearing_deg = distance_m_bearing_deg(
                mission_waypoints[idx - 1][0],
                mission_waypoints[idx - 1][1],
                mission_waypoints[idx][0],
                mission_waypoints[idx][1],
            )
            evtol_fmu_waypoints[idx][3] = (
                bearing_deg if distance_m != 0 else evtol_fmu_waypoints[idx - 1][3]
            )

        # Calculate waypoint gamma (deg)
        if idx == 0:
            evtol_fmu_waypoints[idx][4] = 0.0
        else:
            rise_m = mission_waypoints[idx][2] - mission_waypoints[idx - 1][2]
            curvature_adj_m = R * (
                1 - math.cos(distance_m / DEG2FT / FT2M * math.pi / 180.0)
            )
            evtol_fmu_waypoints[idx][4] = math.degrees(
                math.atan2(rise_m + curvature_adj_m, distance_m)
            )

        # Set waypoint speed and capture distance
        evtol_fmu_waypoints[idx][5] = mission_waypoints[idx][3]
        evtol_fmu_waypoints[idx][6] = mission_waypoints[idx][4]

        # Calculate start speed capture distance before arrival (adjusted for flight path gamma)
        if math.sin(math.radians(evtol_fmu_waypoints[idx][4])) == 0:
            evtol_fmu_waypoints[idx][7] = mission_waypoints[idx][5]
        else:
            evtol_fmu_waypoints[idx][7] = mission_waypoints[idx][5] / math.cos(
                math.radians(evtol_fmu_waypoints[idx][4])
            )

        # Set speed capture duration distance
        evtol_fmu_waypoints[idx][8] = mission_waypoints[idx][6]

    # Read the existing configuration file
    with open(config_filepath, "r") as file:
        sim_config_json = json.load(file)

    # Update the actor's initial position and orientation based on the first calculated location and heading
    sim_config_json["world"]["actors"][vehicle_idx]["transform"]["position"] = [
        evtol_fmu_waypoints[0][0],
        evtol_fmu_waypoints[0][1],
        evtol_fmu_waypoints[0][2],
    ]

    # Update the FMU model initial values for the selected vehicle
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
        math.radians(initial_hdg_deg),
    ]
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"]["num_waypoints"] = (
        float(len(mission_waypoints))
    )
    sim_config_json["fmu_models"][vehicle_idx]["fmu_initial_vals"][
        "waypoints"
    ] = evtol_fmu_waypoints.T.flatten().tolist()

    # Write back the updated configuration
    with open(config_filepath, "w") as file:
        json.dump(sim_config_json, file, indent=4)


# -------------------------------------------------------------------------------------
# Function: Vehicle state receiver callback
# -------------------------------------------------------------------------------------
def on_vehicle_state_data(data, _):
    pos_x = data.state.pose.position.x
    pos_y = data.state.pose.position.y
    pos_z = data.state.pose.position.z
    vel_x = data.velocity.x
    vel_y = data.velocity.y
    vel_z = data.velocity.z
    print(
        f"[ pos_x: {pos_x:.1f}, pos_y: {pos_y:.1f}, pos_z: {pos_z:.1f}, vel_x: {vel_x:.1f}, vel_y: {vel_y:.1f}, vel_z: {vel_z:.1f} ]",
        end="\r",
    )


# -------------------------------------------------------------------------------------
# Main simulation setup for two aircraft
# -------------------------------------------------------------------------------------
# Configuration parameters
ORIGIN_ALTITUDE_M = 265.5  # Altitude at world origin
config_filepath = "config/sim_config_daa_collision.json"

# -----------------------------
# Setup ownship (Vehicle 1)
# -----------------------------
ownship_mission_waypoints = np.genfromtxt(
    "mission_waypoints/mission_waypoint_short.txt", delimiter=","
)
initial_lla = [
    ownship_mission_waypoints[0][0],
    ownship_mission_waypoints[0][1],
    ownship_mission_waypoints[0][2],
]
set_world_origin(initial_lla, ORIGIN_ALTITUDE_M, config_filepath)
set_evtol_vehicle_mission_waypoints(
    0, ownship_mission_waypoints, initial_lla, config_filepath
)

# -----------------------------
# Setup intruder (Vehicle 2)
# -----------------------------
intruder_mission_waypoints = np.genfromtxt(
    "mission_waypoints/mission_waypoint_short_rev.txt", delimiter=","
)
set_evtol_vehicle_mission_waypoints(
    1, intruder_mission_waypoints, initial_lla, config_filepath
)

# --------------------------------------------
# Set up Kafka subscriptions for both aircrafts
# --------------------------------------------
transport = middleware.get_transport("kafka")
transport.subscribe(
    aerosim_types.VehicleState, "aerosim.actor1.vehicle_state", on_vehicle_state_data
)
transport.subscribe(
    aerosim_types.VehicleState, "aerosim.actor2.vehicle_state", on_vehicle_state_data
)

# -------------------------------------------------------------------------------------
# Run the simulation
# -------------------------------------------------------------------------------------
aerosim = AeroSim()
try:
    aerosim.run(config_filepath)
except FileNotFoundError as e:
    print("FileNotFoundError during simulation run:", e)
    raise


try:
    input("Simulation is running. Press any key to stop...")
except KeyboardInterrupt:
    print("Simulation stopped.")
finally:
    aerosim.stop()
