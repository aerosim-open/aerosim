"""
Pilot Control with Flight Deck Example

This example demonstrates how to run a simulation to fly an airplane with a
flight deck in three modes:
  1. Joystick direct control of flight control surfaces (Xbox controller mapping)
  2. Keyboard control of autopilot setpoints (airspeed, altitude, heading)
  3. Autopilot control by flight plan waypoints (example_flight_plan.json)

Usage:
    cd examples
    python pilot_control_with_flight_deck.py

    Enter "1", "2", or "3" to choose the control mode from the options listed above.
    Use keyboard or joystick inputs with the AeroSim App window active:
        
        For mode 1 using an Xbox controller
            - "Y" button increases power (sets throttle to 100%)
            - "A" button decreases power (sets throttle to 0%)
            - Left stick controls roll and pitch
            - Right stick controls yaw

        For mode 2 using the keyboard
            - "Up arrow" key increases airspeed setpoint (non-zero setpoint sets throttle to 100%)
            - "Down arrow" key decreases airspeed setpoint (zero setpoint sets throttle to 0%)
            - "W" key increases altitude setpoint (ascend)
            - "S" key decreases altitude setpoint (descend)
            - "A" key decreases heading setpoint (turn left)
            - "D" key increases heading setpoint (turn right)
            
        For mode 3 using the keyboard
            - Autopilot control automatically flies the flight plan waypoints specified in example_flight_plan.json
            - No keyboard/joystick control

    Ctrl-C breaks the script to stop the simulation.
"""

import time
import threading
import traceback
import asyncio
import json
from typing import Dict, Any

from aerosim import AeroSim
from aerosim_data import types as aerosim_types
from aerosim_data import middleware
from aerosim_core import meters_to_feet

# Import the new websockets implementation
from aerosim.io.websockets import (
    start_websocket_servers,
    DEFAULT_COMMAND_PORT,
    DEFAULT_IMAGE_PORT,
    DEFAULT_DATA_PORT,
)
from aerosim.io.websockets.command_server import command_queue
from aerosim.io.websockets.image_server import on_camera_data
from aerosim.io.websockets.data_server import on_flight_display_data


# --- Constants

# scale joystick input for roll, pitch and yaw
JOYSTICK_LEFT_X_SCALE = 0.7
JOYSTICK_LEFT_Y_SCALE = 0.4
JOYSTICK_RIGHT_X_SCALE = 0.5
JOYSTICK_SCALE = {
    "roll_cmd": JOYSTICK_LEFT_X_SCALE,
    "pitch_cmd": JOYSTICK_LEFT_Y_SCALE,
    "yaw_cmd": JOYSTICK_RIGHT_X_SCALE,
}

# Increment multiplier for button inputs
BUTTON_STEP = 0.02

# Constants for the keyboard control of autopilot setpoints
MAX_AIRSPEED = 200.0  # ft/s
MAX_ALTITUDE = 13500.0  # ft
AIRSPEED_STEP = 5.0  # kts
ALTITUDE_STEP = 50.0  # ft
HEADING_STEP = 5.0  # deg

# ---


# User-selected control mode
class ControlMode:
    JOYSTICK_FC_DIRECT = 0
    KEYBOARD_AP_SETPOINTS = 1
    KEYBOARD_AP_FLIGHT_PLAN = 2

    key = {
        JOYSTICK_FC_DIRECT: "1",
        KEYBOARD_AP_SETPOINTS: "2",
        KEYBOARD_AP_FLIGHT_PLAN: "3",
    }

    description = {
        JOYSTICK_FC_DIRECT: "Joystick direct control of flight control surfaces (Xbox controller mapping).",
        KEYBOARD_AP_SETPOINTS: "Keyboard control of autopilot setpoints (airspeed, altitude, heading).",
        KEYBOARD_AP_FLIGHT_PLAN: "Autopilot control by flight plan waypoints (example_flight_plan.json).",
    }


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


class App:
    """Main application class for flight simulation and control"""

    def __init__(self):
        self.aerosim = None
        self.transport = None
        self.control_mode = ControlMode.JOYSTICK_FC_DIRECT
        self.AutopilotCommand = None
        self.FlightPlanCommand = None
        self.FlightControlCommand = None
        self.fc_cmd = None
        self.ap_cmd = None
        self.fc_cmd_topic = None
        self.ap_cmd_topic = None
        self.lock = None
        self.current_speed = 0
        self.current_altitude = 0

    def clamp_flight_ctrl_cmd(self) -> None:
        """Clamp all flight control commands to valid ranges"""
        powercmd = self.fc_cmd["power_cmd"][0]
        self.fc_cmd["power_cmd"][0] = clamp(powercmd, 0.0, 1.0)

        self.fc_cmd["roll_cmd"] = clamp(self.fc_cmd["roll_cmd"], -1.0, 1.0)
        self.fc_cmd["pitch_cmd"] = clamp(self.fc_cmd["pitch_cmd"], -1.0, 1.0)
        self.fc_cmd["yaw_cmd"] = clamp(self.fc_cmd["yaw_cmd"], -1.0, 1.0)
        self.fc_cmd["thrust_tilt_cmd"] = clamp(self.fc_cmd["thrust_tilt_cmd"], 0.0, 1.0)
        self.fc_cmd["flap_cmd"] = clamp(self.fc_cmd["flap_cmd"], 0.0, 1.0)
        self.fc_cmd["speedbrake_cmd"] = clamp(self.fc_cmd["speedbrake_cmd"], 0.0, 1.0)
        self.fc_cmd["landing_gear_cmd"] = clamp(
            self.fc_cmd["landing_gear_cmd"], 0.0, 1.0
        )
        self.fc_cmd["wheel_steer_cmd"] = clamp(
            self.fc_cmd["wheel_steer_cmd"], -1.0, 1.0
        )
        self.fc_cmd["wheel_brake_cmd"] = clamp(self.fc_cmd["wheel_brake_cmd"], 0.0, 1.0)

    def normalize_heading_deg(self, heading: float) -> float:
        if heading < 0.0:
            heading += 360.0
        if heading >= 360.0:
            heading -= 360.0
        return heading

    def init(self) -> None:
        self.control_mode = ControlMode.JOYSTICK_FC_DIRECT

        print(
            "\nThis example can be run with three options for the user control mode, use the keyboard to select:"
        )
        for i in range(len(ControlMode.key)):
            print(f"\t{ControlMode.key[i]} : {ControlMode.description[i]}")
        print()

        user_control_choice = None
        while user_control_choice not in ControlMode.key.values():
            user_control_choice = input("Select control mode (1, 2, or 3): \n")
        mode = list(ControlMode.key.values()).index(user_control_choice)
        self.control_mode = mode

        print(f"Selected mode: {ControlMode.description[self.control_mode]}")

        """Initialize the simulation and setup command structures"""
        self.FlightControlCommand = aerosim_types.FlightControlCommand().to_dict()

        """
        FlightControlCommand:
        {
            power_cmd: Vec<f64>, // power, 0.0~1.0, array to be able to split vertical lift and horizontal cruise
            roll_cmd: f64,       // roll axis, -1.0~1.0
            pitch_cmd: f64,      // pitch axis, -1.0~1.0
            yaw_cmd: f64,        // yaw axis, -1.0~1.0
            thrust_tilt_cmd: f64, // tilt vtol, 0.0~1.0
            flap_cmd: f64,       // flap, 0.0~1.0, for low speed flight
            speedbrake_cmd: f64, // speedbrake, 0.0~1.0, for fixed-wing
            landing_gear_cmd: f64, // landing gear, 0.0 up ~ 1.0 down
            wheel_steer_cmd: f64, // wheel steering, -1.0~1.0
            wheel_brake_cmd: f64, // wheel brake, 0.0~1.0
        }
        """

        self.FlightPlanCommand = aerosim_types.AutopilotFlightPlanCommand.to_dict()
        """
        AutopilotFlightPlanCommand:
            FlightPlanCommand["Stop"] = 0
            FlightPlanCommand["Run"] = 1
            FlightPlanCommand["Pause"] = 2
        """

        self.AutopilotCommand = aerosim_types.AutopilotCommand().to_dict()
        """
        AutopilotCommand:
        {
            "flight_plan": "",
            "flight_plan_command": 0,
            "use_manual_setpoints": true,
            "attitude_hold": false,
            "altitude_hold": false,
            "altitude_setpoint_ft": 0.0,
            "airspeed_hold": false,
            "airspeed_setpoint_kts": 0.0,
            "heading_hold": false,
            "heading_set_by_waypoint": false,
            "heading_setpoint_deg": 0.0,
            "target_wp_latitude_deg": 0.0,
            "target_wp_longitude_deg": 0.0,
        }
        """

        self.lock = threading.Lock()
        self.current_speed = 0
        self.current_altitude = 0

        # Set up middleware transport
        self.transport = middleware.get_transport("kafka")
        self.fc_cmd_topic = "aerosim.actor1.flight_control_command"
        self.ap_cmd_topic = "aerosim.actor1.autopilot_command"
        # Subscribe to vehicle state topic
        self.transport.subscribe(
            aerosim_types.VehicleState,
            "aerosim.actor1.vehicle_state",
            self.on_vehicle_state_data,
        )
        # Subscribe to camera images topic
        self.transport.subscribe_raw(
            "aerosim::types::CompressedImage",
            "aerosim.renderer.responses",
            on_camera_data,
        )
        # Subscribe to flight data topic
        self.transport.subscribe(
            aerosim_types.PrimaryFlightDisplayData,
            "aerosim.actor1.primary_flight_display_data",
            on_flight_display_data,
        )

        # Run AeroSim simulation
        self.aerosim = AeroSim()
        if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
            self.aerosim.run("config/sim_config_pilot_control_with_flight_deck_fc.json")
        else:
            self.aerosim.run("config/sim_config_pilot_control_with_flight_deck_ap.json")

        print("\n*** Waiting for aircraft to stabilize. ***\n")
        time.sleep(3)

        # Initialize control commands to neutral positions and publish initial control topics
        if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
            self.fc_cmd = self.FlightControlCommand.copy()
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

            # Create the object at the very last moment to avoid pyo3 cloning issues
            # https://pyo3.rs/main/faq.html#pyo3get-clones-my-field
            flight_control_command = aerosim_types.FlightControlCommand(**self.fc_cmd)
            self.transport.publish(self.fc_cmd_topic, flight_control_command)

        elif self.control_mode == ControlMode.KEYBOARD_AP_SETPOINTS:
            self.ap_cmd = self.AutopilotCommand.copy()
            self.ap_cmd["flight_plan"] = ""
            self.ap_cmd["flight_plan_command"] = (
                aerosim_types.AutopilotFlightPlanCommand.Stop
            )
            self.ap_cmd["use_manual_setpoints"] = True
            self.ap_cmd["attitude_hold"] = False
            self.ap_cmd["altitude_hold"] = True
            self.ap_cmd["altitude_setpoint_ft"] = 0.0
            self.ap_cmd["airspeed_hold"] = True
            self.ap_cmd["airspeed_setpoint_kts"] = 0.0
            self.ap_cmd["heading_hold"] = True
            self.ap_cmd["heading_set_by_waypoint"] = False
            self.ap_cmd["heading_setpoint_deg"] = 0.0
            self.ap_cmd["target_wp_latitude_deg"] = 0.0
            self.ap_cmd["target_wp_longitude_deg"] = 0.0

            # Create the object at the very last moment to avoid pyo3 cloning issues
            # https://pyo3.rs/main/faq.html#pyo3get-clones-my-field
            autopilot_command = aerosim_types.AutopilotCommand(**self.ap_cmd)
            self.transport.publish(self.ap_cmd_topic, autopilot_command)

        elif self.control_mode == ControlMode.KEYBOARD_AP_FLIGHT_PLAN:
            with open("example_flight_plan.json") as f:
                flight_plan = json.load(f)
            self.ap_cmd = self.AutopilotCommand.copy()
            self.ap_cmd["use_manual_setpoints"] = False
            self.ap_cmd["flight_plan"] = json.dumps(flight_plan)
            self.ap_cmd["flight_plan_command"] = (
                aerosim_types.AutopilotFlightPlanCommand.Run
            )

            # Create the object at the very last moment to avoid pyo3 cloning issues
            # https://pyo3.rs/main/faq.html#pyo3get-clones-my-field
            autopilot_command = aerosim_types.AutopilotCommand(**self.ap_cmd)
            self.transport.publish(self.ap_cmd_topic, autopilot_command)

    def on_vehicle_state_data(self, data: Dict[str, Any], _) -> None:
        """
        Update vehicle state data

        Args:
            data: Vehicle state data
            _: Unused parameter
        """
        cur_speed = meters_to_feet(data.velocity.x)
        # position in NED (North-East-Down) coordinate system
        cur_altitude = meters_to_feet(-data.state.pose.position.z)

        with self.lock:
            self.current_speed = cur_speed
            self.current_altitude = cur_altitude

    def loop(self) -> None:
        """Main control loop for processing commands and updating simulation"""
        running = True

        try:
            while running:
                with self.lock:
                    veh_state_str = f"Alt: {self.current_altitude:.0f} ft Spd: {self.current_speed:.0f} ft/s"

                if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
                    # Process any pending commands
                    if command_queue:
                        command = command_queue.popleft()
                        print(f"Applying control: {command}")
                        self.apply_control(command)

                    # Ensure commands are within valid ranges
                    self.clamp_flight_ctrl_cmd()

                elif self.control_mode == ControlMode.KEYBOARD_AP_SETPOINTS:
                    # Process any pending commands
                    if command_queue:
                        command = command_queue.popleft()
                        print(f"Applying setpoint: {command}")
                        self.apply_setpoint(command)

                elif self.control_mode == ControlMode.KEYBOARD_AP_FLIGHT_PLAN:
                    # No keyboard control for flight plan mode
                    pass
                else:
                    print("Invalid control mode selected.")
                    break

                # Publish commands to the simulation
                if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
                    # Create the object at the very last moment to avoid pyo3 cloning issues
                    # https://pyo3.rs/main/faq.html#pyo3get-clones-my-field
                    flight_control_command = aerosim_types.FlightControlCommand(
                        **self.fc_cmd
                    )
                    self.transport.publish(self.fc_cmd_topic, flight_control_command)
                else:
                    # Create the object at the very last moment to avoid pyo3 cloning issues
                    # https://pyo3.rs/main/faq.html#pyo3get-clones-my-field
                    autopilot_command = aerosim_types.AutopilotCommand(**self.ap_cmd)
                    self.transport.publish(self.ap_cmd_topic, autopilot_command)

                # Display status text
                if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
                    status_text = f"{veh_state_str}, power: {self.fc_cmd['power_cmd'][0]:.2f}, pitch: {self.fc_cmd['pitch_cmd']:.2f}, roll: {self.fc_cmd['roll_cmd']:.2f}, yaw: {self.fc_cmd['yaw_cmd']:.2f}"
                elif self.control_mode == ControlMode.KEYBOARD_AP_SETPOINTS:
                    status_text = f"{veh_state_str}, airspd_set:{self.ap_cmd['airspeed_setpoint_kts']:.0f} kts, alt_set: {self.ap_cmd['altitude_setpoint_ft']:.0f} ft, heading_set: {self.ap_cmd['heading_setpoint_deg']:.0f} deg"
                elif self.control_mode == ControlMode.KEYBOARD_AP_FLIGHT_PLAN:
                    status_text = (
                        f"{veh_state_str}, autopilot is running in flight plan mode"
                    )
                else:
                    status_text = "Invalid control mode selected."

                print(status_text, end="\r")

                # Limit the update rate
                if self.control_mode == ControlMode.JOYSTICK_FC_DIRECT:
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        except Exception as e:
            print(f"\nError in simulation loop: {e}")
            traceback.print_exc()

    def stop(self) -> None:
        """Stop the AeroSim simulation"""
        if self.aerosim:
            self.aerosim.stop()

    def apply_control(self, command: Dict[str, Any]) -> None:
        """
        Apply control commands from gamepad inputs

        Args:
            command: Control command dictionary with command, value, and source
        """
        cmd_name = command["command"]
        cmd_value = command["value"]
        cmd_source = command["source"]

        # Continuous inputs from gamepad
        if cmd_source == "gamepad":
            if cmd_name == "power_cmd":
                self.fc_cmd["power_cmd"][0] += BUTTON_STEP * cmd_value
            elif cmd_name == "left_stick_x":
                self.fc_cmd["roll_cmd"] = float(cmd_value) * JOYSTICK_SCALE["roll_cmd"]
            elif cmd_name == "left_stick_y":
                self.fc_cmd["pitch_cmd"] = (
                    -float(cmd_value) * JOYSTICK_SCALE["pitch_cmd"]
                )
            elif cmd_name == "right_stick_x":
                self.fc_cmd["yaw_cmd"] = -float(cmd_value) * JOYSTICK_SCALE["yaw_cmd"]
            elif cmd_name in ["wheel_steer_cmd", "wheel_brake_cmd"]:
                self.fc_cmd[cmd_name] += BUTTON_STEP * cmd_value
            else:
                print(f"Command not valid: {command}")

    def apply_setpoint(self, command: Dict[str, Any]) -> None:
        """
        Apply setpoints from keyboard inputs

        Args:
            command: Control command dictionary with command, value, and source
        """
        cmd_name = command["command"]
        cmd_value = command["value"]
        cmd_source = command["source"]

        # Continuous inputs from gamepad
        if cmd_source == "keyboard":
            if cmd_name == "airspeed_setpoint_kts":
                self.ap_cmd["airspeed_setpoint_kts"] += AIRSPEED_STEP * cmd_value
                self.ap_cmd["airspeed_setpoint_kts"] = clamp(
                    self.ap_cmd["airspeed_setpoint_kts"], 0.0, MAX_AIRSPEED
                )
            elif cmd_name == "heading_setpoint_deg":
                self.ap_cmd["heading_setpoint_deg"] += HEADING_STEP * cmd_value
                self.ap_cmd["heading_setpoint_deg"] = self.normalize_heading_deg(
                    self.ap_cmd["heading_setpoint_deg"]
                )
            elif cmd_name == "altitude_setpoint_ft":
                self.ap_cmd["altitude_setpoint_ft"] += ALTITUDE_STEP * cmd_value
                self.ap_cmd["altitude_setpoint_ft"] = clamp(
                    self.ap_cmd["altitude_setpoint_ft"], 0.0, MAX_ALTITUDE
                )
            else:
                print(f"Command not valid: {command}")


async def run_websocket_servers():
    """Run the WebSocket servers for communication with aerosim-app"""
    # logger.info("Starting WebSocket servers for aerosim-app communication...")
    # Start all three WebSocket servers (command, image, data)
    websocket_tasks = await start_websocket_servers(
        command_port=DEFAULT_COMMAND_PORT,
        image_port=DEFAULT_IMAGE_PORT,
        data_port=DEFAULT_DATA_PORT,
    )
    # Wait for all servers to complete (they run indefinitely)
    await asyncio.gather(*websocket_tasks)


def run_simulation() -> None:
    """Run the simulation in a separate thread"""
    app = App()
    try:
        app.init()
        app.loop()
    finally:
        app.stop()


if __name__ == "__main__":
    try:
        # Start the simulation in a separate thread
        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()

        # Start the WebSocket server in the main asyncio event loop
        asyncio.run(run_websocket_servers())
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
