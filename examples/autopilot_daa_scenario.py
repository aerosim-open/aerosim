"""
Autopilot DAA (Detect and Avoid) Scenario Example

This example demonstrates how to use the aerosim package to:
1. Run a simulation with autopilot following predefined waypoints
2. Stream camera images and flight data to aerosim-app

This example loads waypoints from a file, configures the simulation,
and runs the autopilot in waypoint-following mode.

Usage:
    cd examples
    python autopilot_daa_scenario.py

    The EVTOL aircraft will take off and follow the waypoints defined in the
    mission_waypoints/mission_waypoint_square.txt file under autopilot control.

    During the flight, an intruder airplane will fly towards the EVTOL
    aircraft to simulate a potential DAA situation. With the AeroSim App window
    active you can take manual control to avoid a collision by using an Xbox
    controller:
        
        - "B" button activates manual control

        In hover mode (low speed):
            - Left stick controls yaw and altitude
            - Right stick controls forward speed and lateral speed  
        
        In forward flight mode (high speed):
            - Left stick controls pitch and yaw
            - Right stick controls forward speed and roll
        
    Ctrl-C breaks the script to stop the simulation.
"""

import math
import numpy as np
import time
import json
import threading
import traceback
import asyncio
import os
import logging
from typing import Tuple

# Import aerosim dependencies
from aerosim import AeroSim
from aerosim_data import types as aerosim_types
from aerosim_data import middleware
from aerosim_core import lla_to_ned

# Import WebSocket server functionality
from aerosim.io.websockets import (
    start_websocket_servers,
    DEFAULT_COMMAND_PORT,
    DEFAULT_IMAGE_PORT,
    DEFAULT_DATA_PORT,
)
from aerosim.io.websockets.command_server import command_queue
from aerosim.io.websockets.image_server import on_camera_data
from aerosim.io.websockets.data_server import on_flight_display_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aerosim.daa_scenario")


# -------------------------------------------------------------------------------------
# Function: Calculate spherical arc distance and bearing between two LLAs
# -------------------------------------------------------------------------------------
def distance_m_bearing_deg(
    lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float
) -> Tuple[float, float]:
    """
    Calculate spherical arc distance and bearing between two LLAs (Haversine)

    Args:
        lat1_deg: Origin Latitude in degree
        lon1_deg: Origin Longitude in degree
        lat2_deg: Destination Latitude in degree
        lon2_deg: Destination Longitude in degree

    Returns:
        Tuple containing distance in meters and bearing in degrees
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

    # Return distance in meters
    return R * c, bearing


# -------------------------------------------------------------------------------------
# Setup mission waypoints
# -------------------------------------------------------------------------------------
def setup_mission_waypoints() -> None:
    """
    Setup mission waypoints and update the simulation configuration file
    """
    # Configurations
    ORIGIN_ALTITUDE_M = -5.0  # Initial altitude at origin

    # Constants
    KTS2MPS = 0.514444  # Knots to meters per second
    R = 6372800.0  # For Earth radius in meters
    DEG2FT = 60.0 * 6076.0  # Degree to feet
    FT2M = 0.3048  # Feet to meter

    # Get the script directory to handle paths correctly
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Read mission waypoints
    # [Latitude_deg, Longitude_deg, Altitude_m, Wypt_Speed_m/s, Wypt_Capture_Distance_m,
    # Start_Speed_Capture_Distance_Befor_Arrival_m, Speed_Capture_Duration_Distance_m]
    waypoints_path = os.path.join(
        script_dir, "mission_waypoints/mission_waypoint_square.txt"
    )
    mission_waypoints = np.genfromtxt(waypoints_path, delimiter=",")

    # Log waypoint count without printing the entire list
    logger.info(f"Loaded {len(mission_waypoints)} waypoints from waypoint file")

    # Create waypoint structure for evtol_vehicle_fmu mask parameter
    # [North_m, East_m, Down_m, Heading_deg, Gama_deg, Wypt_Speed_m/s, Wypt_Capture_Distance_m,
    # Start_Speed_Capture_Distance_Befor_Arrival_m, Speed_Capture_Duration_Distance_m]
    evtol_fmu_waypoints = np.zeros((100, 9))

    # Calculate initial vehicle position and heading (initial heading is calculated between first and third waypoint)
    initial_lla = [
        mission_waypoints[0][0],
        mission_waypoints[0][1],
        mission_waypoints[0][2],
    ]
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
            evtol_fmu_waypoints[idx][7] = mission_waypoints[idx][5]
        else:
            # Adjust for slant range due to automatically calculated gamma waypoint frame
            evtol_fmu_waypoints[idx][7] = round(
                mission_waypoints[idx][5]
                / math.cos(math.radians(evtol_fmu_waypoints[idx][4])),
                1,
            )

        # Set Speed_Capture_Duration_Distance_m
        evtol_fmu_waypoints[idx][8] = mission_waypoints[idx][6]

    # Read original scenario file
    config_path = os.path.join(
        script_dir, "config/sim_config_autopilot_daa_scenario.json"
    )
    sim_config_json = []
    with open(config_path, "r") as file:
        sim_config_json = json.load(file)

    # Modify world origin and vehicle initial orientation
    sim_config_json["world"]["origin"]["latitude"] = initial_lla[0]
    sim_config_json["world"]["origin"]["longitude"] = initial_lla[1]
    sim_config_json["world"]["origin"]["altitude"] = ORIGIN_ALTITUDE_M
    sim_config_json["world"]["actors"][0]["transform"]["rotation"] = [
        0.0,
        0.0,
        round(initial_hdg_deg, 1),
    ]

    # Setup evtol_vehicle_fmu mask parameter
    sim_config_json["fmu_models"][0]["fmu_initial_vals"]["init_wypt_num"] = 1.0
    sim_config_json["fmu_models"][0]["fmu_initial_vals"]["init_ned_m"] = [0.0, 0.0, 0.0]
    sim_config_json["fmu_models"][0]["fmu_initial_vals"]["init_rpy_rad"] = [
        0.0,
        0.0,
        round(math.radians(initial_hdg_deg), 6),
    ]
    sim_config_json["fmu_models"][0]["fmu_initial_vals"]["num_waypoints"] = float(
        len(mission_waypoints)
    )
    sim_config_json["fmu_models"][0]["fmu_initial_vals"]["waypoints"] = (
        evtol_fmu_waypoints.T.flatten().tolist()
    )

    # Write updated config file
    with open(config_path, "w") as file:
        json.dump(sim_config_json, file, indent=4)

    logger.info(f"Updated simulation configuration with waypoints")

    return initial_hdg_deg


# -------------------------------------------------------------------------------------
# Function Vehicle state receiver callback
# -------------------------------------------------------------------------------------
def on_vehicle_state_data(data, _):
    """
    Callback function for vehicle state data

    Args:
        data: Vehicle state data
        _: Unused parameter
    """
    pos_x = data.state.pose.position.x
    pos_y = data.state.pose.position.y
    pos_z = data.state.pose.position.z
    vel_x = data.velocity.x
    vel_y = data.velocity.y
    vel_z = data.velocity.z

    # Log vehicle state at debug level to avoid cluttering the console
    logger.debug(
        f"Position: [{pos_x:.1f}, {pos_y:.1f}, {pos_z:.1f}], Velocity: [{vel_x:.1f}, {vel_y:.1f}, {vel_z:.1f}]"
    )


class DAAScenario:
    """Main class for the Autopilot DAA Scenario"""

    def __init__(self):
        """Initialize the DAA Scenario application"""
        self.aerosim = None
        self.transport = None
        self.running = True
        self.manual_override = 0.0  # Add manual override flag
        self.control_data_dict = {
            "manual_override": self.manual_override,
            "left_stick_x": 0.0,
            "left_stick_y": 0.0,
            "right_stick_x": 0.0,
            "right_stick_y": 0.0,
        }

        # Get the script directory to handle paths correctly
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    def init(self):
        """Initialize the simulation and middleware"""
        # Setup mission waypoints
        setup_mission_waypoints()

        # Initialize middleware
        self.transport = middleware.get_transport("kafka")

        # Subscribe to vehicle state topic
        self.transport.subscribe(
            aerosim_types.VehicleState,
            "aerosim.actor1.vehicle_state",
            on_vehicle_state_data,
        )

        # Subscribe to camera topic for streaming to aerosim-app
        self.transport.subscribe_raw(
            "aerosim::types::CompressedImage",
            "aerosim.renderer.responses",
            on_camera_data,
        )

        # Subscribe to flight data topic for streaming to aerosim-app
        self.transport.subscribe(
            aerosim_types.PrimaryFlightDisplayData,
            "aerosim.actor1.primary_flight_display_data",
            on_flight_display_data,
        )

        # Run AeroSim simulation
        config_path = os.path.join(
            self.script_dir, "config/sim_config_autopilot_daa_scenario.json"
        )
        logger.info(f"Starting AeroSim simulation with config: {config_path}")
        self.aerosim = AeroSim()
        self.aerosim.run(config_path)

        # Send initial command to evtol_vehicle to establish initial connection
        self.transport.publish(
            "aerosim.actor1.evtol_vehicle.aux_in", self.control_data_dict
        )

        logger.info("Simulation initialized. Waiting for aircraft to stabilize...")
        time.sleep(3)
        logger.info(
            "Autopilot is following waypoints. Commands from aerosim-app will be processed."
        )

    def run(self):
        """Run the simulation loop"""
        try:
            # Run until user interrupts
            while self.running:
                # Process any commands from aerosim-app
                if command_queue:
                    command = command_queue.popleft()  # Use popleft() instead of pop() to process commands in FIFO order
                    logger.info(f"Received command from aerosim-app: {command}")

                    # Handle A button press for manual override
                    if (
                        command.get("command") == "manual_override"
                        and command.get("value") == 1.0
                    ):
                        self.manual_override = 1.0
                        self.control_data_dict["manual_override"] = self.manual_override
                        logger.info("Manual override activated! Taking manual control.")

                    # Process joystick inputs when in manual override mode
                    if self.manual_override == 1.0:
                        # Map gamepad controls to joystick values
                        if command.get("source") == "gamepad":
                            # Direct stick commands that match FMU input mapping
                            if command.get("command") in [
                                "left_stick_x",
                                "left_stick_y",
                                "right_stick_x",
                                "right_stick_y",
                            ]:
                                self.control_data_dict[command.get("command")] = float(
                                    command.get("value")
                                )

                            # Deadzone is already applied in aerosim-app, so we don't need to apply it again
                            # Publish joystick command to evtol_vehicle
                            self.transport.publish(
                                "aerosim.actor1.evtol_vehicle.aux_in",
                                self.control_data_dict,
                            )
                            logger.debug(
                                f"Published manual control: {self.control_data_dict}"
                            )

                # Run at 50Hz
                time.sleep(0.02)

        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            # Clean up
            if self.aerosim:
                self.aerosim.stop()
            logger.info("Simulation stopped")


def run_simulation():
    """Run the simulation in a separate thread"""
    # Create the application
    app = DAAScenario()

    try:
        # Initialize the simulation
        app.init()

        # Run the simulation loop
        app.run()
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        traceback.print_exc()
    finally:
        # Stop the simulation
        app.running = False


async def run_websocket_servers():
    """Run the WebSocket servers for communication with aerosim-app"""
    logger.info("Starting WebSocket servers for aerosim-app communication...")
    # Start all three WebSocket servers (command, image, data)
    websocket_tasks = await start_websocket_servers(
        command_port=DEFAULT_COMMAND_PORT,
        image_port=DEFAULT_IMAGE_PORT,
        data_port=DEFAULT_DATA_PORT,
    )
    # Wait for all servers to complete (they run indefinitely)
    await asyncio.gather(*websocket_tasks)


if __name__ == "__main__":
    try:
        # Start the simulation in a separate thread
        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()

        # Start the WebSocket server in the main asyncio event loop
        asyncio.run(run_websocket_servers())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
