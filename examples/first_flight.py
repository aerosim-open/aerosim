"""
First Flight with App Example

This example demonstrates how to use the aerosim package to:
1. Run a simulation with WebSockets support for communication with aerosim-app
2. Process input commands from aerosim-app
3. Stream camera images and flight data to aerosim-app

This is a simplified example that shows the core functionality of the aerosim package.

Usage:
    # Run from the aerosim root directory:
    python examples/first_flight.py

    # Or run from the examples directory:
    cd examples
    python first_flight.py

    The airplane will take off under autopilot control, but with the AeroSim App window active you 
    can use the keyboard to adjust the autopilot setpoints:
        - "Up arrow" key increases airspeed setpoint (non-zero setpoint sets throttle to 100%)
        - "Down arrow" key decreases airspeed setpoint (zero setpoint sets throttle to 0%)
        - "W" key increases altitude setpoint (ascend)
        - "S" key decreases altitude setpoint (descend)
        - "A" key decreases heading setpoint (turn left)
        - "D" key increases heading setpoint (turn right)

    Ctrl-C breaks the script to stop the simulation.
"""

import asyncio
import threading
import time
import logging
import os
import traceback
from typing import Dict, Any

# Import aerosim dependencies
from aerosim import AeroSim
from aerosim_data import types as aerosim_types
from aerosim_data import middleware

# Import WebSocket server functionality
from aerosim.io.websockets import (
    start_websocket_servers,
    DEFAULT_COMMAND_PORT,
    DEFAULT_IMAGE_PORT,
    DEFAULT_DATA_PORT
)
from aerosim.io.websockets.command_server import command_queue
from aerosim.io.websockets.image_server import on_camera_data
from aerosim.io.websockets.data_server import on_flight_display_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aerosim.flight_app")

# Constants for autopilot control
AIRSPEED_STEP = 5.0  # kts
ALTITUDE_STEP = 100.0  # ft
HEADING_STEP = 5.0  # deg
MAX_AIRSPEED = 200.0  # kts
MAX_ALTITUDE = 10000.0  # ft

# Helper function to clamp values
def clamp(n: float, minn: float, maxn: float) -> float:
    """
    Clamp a value between a minimum and maximum value

    Args:
        n: Value to clamp
        minn: Minimum allowed value
        maxn: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min(maxn, n), minn)

# Helper function to normalize heading
def normalize_heading_deg(heading: float) -> float:
    """
    Normalize heading to be between 0 and 360 degrees

    Args:
        heading: Heading in degrees

    Returns:
        Normalized heading in degrees
    """
    while heading >= 360.0:
        heading -= 360.0
    while heading < 0.0:
        heading += 360.0
    return heading

class FirstFlight:
    """Simple flight application that connects to aerosim-app"""

    def __init__(self, config_file: str = "config/sim_config_pilot_control_with_flight_deck_ap.json"):
        """
        Initialize the simple flight application

        Args:
            config_file: Path to the simulation configuration file
        """
        # Get the script directory to handle paths correctly
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Use absolute path for config file
        if not os.path.isabs(config_file):
            self.config_file = os.path.join(self.script_dir, config_file)
        else:
            self.config_file = config_file

        logger.info(f"Using config file: {self.config_file}")

        self.aerosim = None
        self.transport = None
        self.running = True

        # Flight control command (for direct control)
        self.fc_cmd = None
        self.fc_cmd_topic = "aerosim.actor1.flight_control_command"

        # Autopilot command (for autopilot control)
        self.ap_cmd = None
        self.ap_cmd_topic = "aerosim.actor1.autopilot_command"

        # Current vehicle state
        self.current_speed = 0.0
        self.current_altitude = 0.0
        self.current_heading = 0.0

        # Thread synchronization
        self.lock = threading.Lock()

    def init(self):
        """Initialize the simulation and middleware"""
        # Initialize middleware
        self.transport = middleware.get_transport("kafka")

        # Subscribe to vehicle state topic
        self.transport.subscribe(
            aerosim_types.VehicleState,
            "aerosim.actor1.vehicle_state",
            self.on_vehicle_state_data,
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

        # Initialize autopilot command
        self.ap_cmd = aerosim_types.AutopilotCommand().to_dict()
        self.ap_cmd["flight_plan"] = ""
        self.ap_cmd["flight_plan_command"] = aerosim_types.AutopilotFlightPlanCommand.Stop
        self.ap_cmd["use_manual_setpoints"] = True
        self.ap_cmd["attitude_hold"] = False
        self.ap_cmd["altitude_hold"] = True
        self.ap_cmd["altitude_setpoint_ft"] = 1000.0  # Initial altitude setpoint
        self.ap_cmd["airspeed_hold"] = True
        self.ap_cmd["airspeed_setpoint_kts"] = 80.0  # Initial airspeed setpoint
        self.ap_cmd["heading_hold"] = True
        self.ap_cmd["heading_set_by_waypoint"] = False
        self.ap_cmd["heading_setpoint_deg"] = 0.0  # Initial heading setpoint (north)
        self.ap_cmd["target_wp_latitude_deg"] = 0.0
        self.ap_cmd["target_wp_longitude_deg"] = 0.0

        # Initialize flight control command (for direct control if needed)
        self.fc_cmd = aerosim_types.FlightControlCommand().to_dict()
        self.fc_cmd["power_cmd"] = [0.0]
        self.fc_cmd["roll_cmd"] = 0.0
        self.fc_cmd["pitch_cmd"] = 0.0
        self.fc_cmd["yaw_cmd"] = 0.0
        self.fc_cmd["thrust_tilt_cmd"] = 0.0
        self.fc_cmd["flap_cmd"] = 0.0
        self.fc_cmd["speedbrake_cmd"] = 0.0
        self.fc_cmd["landing_gear_cmd"] = 0.0
        self.fc_cmd["wheel_steer_cmd"] = 0.0
        self.fc_cmd["wheel_brake_cmd"] = 0.0

        # Set environment variables for JSBSim to find the correct paths
        os.environ["JSBSIM_ROOT_DIR"] = os.path.join(self.script_dir, "jsbsim_xml")

        # Run AeroSim simulation with autopilot config
        logger.info(f"Starting AeroSim simulation with config: {self.config_file}")
        self.aerosim = AeroSim()
        self.aerosim.run(self.config_file)

        # Publish initial autopilot command
        autopilot_command = aerosim_types.AutopilotCommand(**self.ap_cmd)
        self.transport.publish(self.ap_cmd_topic, autopilot_command)

        logger.info("Simulation initialized. Waiting for aircraft to stabilize...")
        time.sleep(3)
        logger.info("Ready to receive commands from aerosim-app")

    def on_vehicle_state_data(self, data, _):
        """Update vehicle state data"""
        # Extract speed, altitude, and heading from vehicle state
        cur_speed = data.velocity.x * 3.28084  # Convert m/s to ft/s
        cur_altitude = -data.state.pose.position.z * 3.28084  # Convert m to ft

        with self.lock:
            self.current_speed = cur_speed
            self.current_altitude = cur_altitude

    def process_command(self, command: Dict[str, Any]):
        """
        Process a command from aerosim-app

        Args:
            command: Command dictionary with command, value, and source
        """
        cmd_name = command["command"]
        cmd_value = float(command["value"])
        cmd_source = command["source"]

        logger.info(f"Processing command: {cmd_name}, value: {cmd_value}, source: {cmd_source}")

        # Apply command to autopilot setpoints based on aerosim-app keyboard.tsx mapping
        if cmd_name == "airspeed_setpoint_kts":
            self.ap_cmd["airspeed_setpoint_kts"] += AIRSPEED_STEP * cmd_value
            self.ap_cmd["airspeed_setpoint_kts"] = clamp(
                self.ap_cmd["airspeed_setpoint_kts"], 0.0, MAX_AIRSPEED
            )
            logger.info(f"Updated airspeed setpoint: {self.ap_cmd['airspeed_setpoint_kts']:.1f} kts")

        elif cmd_name == "heading_setpoint_deg":
            self.ap_cmd["heading_setpoint_deg"] += HEADING_STEP * cmd_value
            self.ap_cmd["heading_setpoint_deg"] = normalize_heading_deg(
                self.ap_cmd["heading_setpoint_deg"]
            )
            logger.info(f"Updated heading setpoint: {self.ap_cmd['heading_setpoint_deg']:.1f} deg")

        elif cmd_name == "altitude_setpoint_ft":
            self.ap_cmd["altitude_setpoint_ft"] += ALTITUDE_STEP * cmd_value
            self.ap_cmd["altitude_setpoint_ft"] = clamp(
                self.ap_cmd["altitude_setpoint_ft"], 0.0, MAX_ALTITUDE
            )
            logger.info(f"Updated altitude setpoint: {self.ap_cmd['altitude_setpoint_ft']:.1f} ft")

        # Publish updated autopilot command
        autopilot_command = aerosim_types.AutopilotCommand(**self.ap_cmd)
        self.transport.publish(self.ap_cmd_topic, autopilot_command)

    def run(self):
        """Run the simulation loop"""
        logger.info("Starting simulation loop")

        try:
            while self.running:
                # Process any commands from aerosim-app
                if command_queue:
                    with self.lock:
                        command = command_queue.popleft()
                        self.process_command(command)

                # Sleep to avoid high CPU usage
                time.sleep(0.01)

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
    program = FirstFlight()

    try:
        # Initialize the simulation
        program.init()

        # Run the simulation loop
        program.run()
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        traceback.print_exc()
    finally:
        # Stop the simulation
        program.running = False

async def run_websocket_servers():
    """Run the WebSocket servers for communication with aerosim-app"""
    logger.info("Starting WebSocket servers for aerosim-app communication...")
    # Start all three WebSocket servers (command, image, data)
    websocket_tasks = await start_websocket_servers(
        command_port=DEFAULT_COMMAND_PORT,
        image_port=DEFAULT_IMAGE_PORT,
        data_port=DEFAULT_DATA_PORT
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
        logger.error(f"Error: {e}")
        traceback.print_exc()
