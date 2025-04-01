from aerosim_core import (
    register_fmu3_var,
    register_fmu3_param,
    haversine_distance_meters,
    meters_to_feet,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import os
import numpy as np
import jsbsim
import json

from pythonfmu3 import Fmi3Slave


FlightPlanCommand = aerosim_types.AutopilotFlightPlanCommand.to_dict()


# Note: The class name is used as the FMU file name
class jsbsim_autopilot_controller_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.aerosim_root_path = os.getenv("AEROSIM_ROOT")
        self.jsbsim = None
        # JSBSIM_DEBUG: 0 = disable JSBSIM console output, 1 = normal output
        os.environ["JSBSIM_DEBUG"] = "0"
        self.flight_plan = None
        self.flight_plan_state = FlightPlanCommand["Stop"]
        self.flight_plan_step = 0

        # ---------------------------------------------------------------------

        # Define Aerosim interface input variables
        self.autopilot_command = dict_to_namespace(
            aerosim_types.AutopilotCommand().to_dict()
        )

        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())

        register_fmu3_var(self, "autopilot_command", causality="input")
        register_fmu3_var(self, "vehicle_state", causality="input")

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables
        self.flight_control_command = dict_to_namespace(
            aerosim_types.FlightControlCommand().to_dict()
        )

        # Note: for array variables, need to set initial values as a numpy array and
        # define the dimensions for the number of elements to build into the FMU
        self.flight_control_command.power_cmd = np.array([0.0])

        register_fmu3_var(self, "flight_control_command", causality="output")

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = (
            "Implementation of a JSBSim fixed-wing autopilot controller model"
        )

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define JSBSim-specific auxiliary parameters

        self.jsbsim_root_dir = "jsbsim_xml/"
        self.jsbsim_script = "scripts/c3104_autopilot_controller.xml"

        register_fmu3_param(self, "jsbsim_root_dir")
        register_fmu3_param(self, "jsbsim_script")

        # JSBSim state variables for c310ap.xml
        self.attitude_phi_rad = 0.0
        self.attitude_heading_true_rad = 0.0
        self.position_h_sl_ft = 0.0
        self.velocities_h_dot_fps = 0.0
        self.fcs_elevator_pos_deg = 0.0
        self.aero_beta_rad = 0.0
        self.velocities_ve_kts = 0.0

        register_fmu3_var(self, "attitude_phi_rad", causality="input")
        register_fmu3_var(self, "attitude_heading_true_rad", causality="input")
        register_fmu3_var(self, "position_h_sl_ft", causality="input")
        register_fmu3_var(self, "velocities_h_dot_fps", causality="input")
        register_fmu3_var(self, "fcs_elevator_pos_deg", causality="input")
        register_fmu3_var(self, "aero_beta_rad", causality="input")
        register_fmu3_var(self, "velocities_ve_kts", causality="input")

        # JSBSim geodetic position for GNCUtilities.xml
        self.position_lat_geod_rad = 0.0
        self.position_long_gc_rad = 0.0

        register_fmu3_var(self, "position_lat_geod_rad", causality="input")
        register_fmu3_var(self, "position_long_gc_rad", causality="input")

        # Output autopilot target info for PFD
        self.target_altitude_ft = 0.0
        self.target_wp_active = False
        self.target_wp_latitude_deg = 0.0
        self.target_wp_longitude_deg = 0.0

        register_fmu3_var(self, "target_altitude_ft", causality="output")
        register_fmu3_var(self, "target_wp_active", causality="output")
        register_fmu3_var(self, "target_wp_latitude_deg", causality="output")
        register_fmu3_var(self, "target_wp_longitude_deg", causality="output")

        # ---------------------------------------------------------------------

    # Map implementation variables to interface variables
    def get_inputs_from_aerosim(self):
        # Copy inputs from the Aerosim interface variables to the JSBSim flight controller

        # Copy JSBSim auxiliary state variables
        # TODO Use vehicle_state msg instead of auxiliary state variables
        self.jsbsim["ext/attitude/phi-rad"] = self.attitude_phi_rad
        self.jsbsim["ext/attitude/heading-true-rad"] = self.attitude_heading_true_rad
        self.jsbsim["ext/position/h-sl-ft"] = self.position_h_sl_ft
        self.jsbsim["ext/velocities/h-dot-fps"] = self.velocities_h_dot_fps
        self.jsbsim["ext/fcs/elevator-pos-deg"] = self.fcs_elevator_pos_deg
        self.jsbsim["ext/aero/beta-rad"] = self.aero_beta_rad
        self.jsbsim["ext/velocities/ve-kts"] = self.velocities_ve_kts
        self.jsbsim["ext/position/lat-geod-rad"] = self.position_lat_geod_rad
        self.jsbsim["ext/position/long-gc-rad"] = self.position_long_gc_rad

        # Commanding manual setpoints takes priority and pauses a running flight plan
        if self.autopilot_command.use_manual_setpoints:
            if self.flight_plan_state == FlightPlanCommand["Run"]:
                self.flight_plan_state = FlightPlanCommand["Pause"]

            self.jsbsim["ap/attitude_hold"] = self.autopilot_command.attitude_hold

            self.jsbsim["ap/altitude_hold"] = self.autopilot_command.altitude_hold
            self.jsbsim["ap/altitude_setpoint"] = (
                self.autopilot_command.altitude_setpoint_ft
            )

            # Set output autopilot target info for PFD
            self.target_altitude_ft = self.autopilot_command.altitude_setpoint_ft

            # Current JSBSim autopilot controller doesn't handle airspeed_setpoint
            # so autopilot_command.airspeed_hold is manually passed through
            # in set_outputs_to_aerosim() instead.
            # self.jsbsim["ap/airspeed_hold"] = self.autopilot_command.airspeed_hold
            # self.jsbsim["ap/airspeed_setpoint"] = (
            #     self.autopilot_command.airspeed_setpoint_kts
            # )

            self.jsbsim["ap/heading_hold"] = self.autopilot_command.heading_hold
            if self.autopilot_command.heading_set_by_waypoint:
                self.jsbsim["ap/heading-setpoint-select"] = 1
                self.jsbsim["guidance/target_wp_latitude_rad"] = np.radians(
                    self.autopilot_command.target_wp_latitude_deg
                )
                self.jsbsim["guidance/target_wp_longitude_rad"] = np.radians(
                    self.autopilot_command.target_wp_longitude_deg
                )

                # Set output autopilot target info for PFD
                self.target_wp_active = True
                self.target_wp_latitude_deg = (
                    self.autopilot_command.target_wp_latitude_deg
                )
                self.target_wp_longitude_deg = (
                    self.autopilot_command.target_wp_longitude_deg
                )
            else:
                self.jsbsim["ap/heading-setpoint-select"] = 0
                self.jsbsim["ap/heading_setpoint"] = (
                    self.autopilot_command.heading_setpoint_deg
                )

                # Set output autopilot target info for PFD
                self.target_wp_active = False
                self.target_wp_latitude_deg = 0.0
                self.target_wp_longitude_deg = 0.0
        else:
            self.execute_flight_plan()

    def set_outputs_to_aerosim(self):
        if self.jsbsim is None:
            return

        # Example JSBSim flight controller doesn't handle airspeed_setpoint
        # self.flight_control_command.power_cmd[0] = self.jsbsim["ap/throttle-cmd-norm"]

        # Passthrough simple throttle command as full throttle for any
        # non-zero airspeed_setpoint with airspace_hold enabled
        if self.autopilot_command.airspeed_hold:
            if self.autopilot_command.airspeed_setpoint_kts > 0.0:
                self.flight_control_command.power_cmd[0] = 1.0
            else:
                self.flight_control_command.power_cmd[0] = 0.0

        self.flight_control_command.roll_cmd = self.jsbsim["ap/aileron_cmd"]
        self.flight_control_command.pitch_cmd = self.jsbsim["ap/elevator_cmd"]
        self.flight_control_command.yaw_cmd = self.jsbsim["ap/rudder_cmd"]

        # No handling of thrust_tilt_cmd in JSBSim autopilot
        # No handling of flap_cmd in JSBSim autopilot
        # No handling of speedbrake_cmd in JSBSim autopilot

        # No handling of landing_gear_cmd in JSBSim autopilot

        # Automatically raise landing gear above 40 ft altitude
        if self.position_h_sl_ft > 40.0:
            self.flight_control_command.landing_gear_cmd = 0.0
        else:
            self.flight_control_command.landing_gear_cmd = 1.0

        # No handling of wheel_steer_cmd in JSBSim autopilot
        # No handling of wheel_brake_cmd in JSBSim autopilot

    # ---------------------------------------------------------------------

    def execute_flight_plan(self):
        if (
            self.flight_plan_state == FlightPlanCommand["Stop"]
            and self.autopilot_command.flight_plan_command == FlightPlanCommand["Run"]
        ):
            # Load and start a new flight plan
            self.flight_plan = json.loads(self.autopilot_command.flight_plan)
            self.flight_plan_step = 0
            self.flight_plan_state = FlightPlanCommand["Run"]
            print("*** Starting new flight plan. ***")
            # Execute the first step
            cur_step = self.flight_plan[self.flight_plan_step]
            print(f"Executing flight plan step {self.flight_plan_step}: {cur_step}")
            self.execute_flight_plan_step(cur_step)

        elif (
            self.flight_plan_state == FlightPlanCommand["Run"]
            and self.autopilot_command.flight_plan_command == FlightPlanCommand["Run"]
        ):
            # Continue running the current flight plan
            cur_step = self.flight_plan[self.flight_plan_step]
            self.execute_flight_plan_step(cur_step)
            is_cur_step_complete = self.check_completion_criteria(cur_step)

            if is_cur_step_complete:
                if self.flight_plan_step < len(self.flight_plan) - 1:
                    self.flight_plan_step += 1
                    cur_step = self.flight_plan[self.flight_plan_step]
                    print(
                        f"Executing flight plan step {self.flight_plan_step}: {cur_step}"
                    )
                else:
                    self.flight_plan_state = FlightPlanCommand["Stop"]
                    self.autopilot_command.flight_plan_command = FlightPlanCommand[
                        "Stop"
                    ]
                    # TODO Stop from immediately getting overwritten back to Run by
                    # last published topic's run command
                    print("Flight plan completed.")

        elif (
            self.flight_plan_state == FlightPlanCommand["Run"]
            and self.autopilot_command.flight_plan_command == FlightPlanCommand["Stop"]
        ):
            # Stop the in-progress flight plan
            self.flight_plan_state = FlightPlanCommand["Stop"]

    def execute_flight_plan_step(self, cur_step):
        if cur_step["command"] == "takeoff":
            # print(
            #     f"Processing takeoff command: cur vel = {self.velocities_ve_kts:.1f} knots"
            # )
            self.jsbsim["ap/heading_hold"] = True
            self.jsbsim["ap/heading_setpoint"] = cur_step["heading_deg"]

            # Pass through throttle command for takeoff
            self.flight_control_command.power_cmd[0] = cur_step["throttle"]

            if self.velocities_ve_kts >= cur_step["takeoff_speed_kts"]:
                self.jsbsim["ap/altitude_hold"] = True
                self.jsbsim["ap/altitude_setpoint"] = cur_step["target_altitude_ft"]

            # Set output autopilot target info for PFD
            self.target_altitude_ft = cur_step["target_altitude_ft"]
            self.target_wp_active = False
            self.target_wp_latitude_deg = 0.0
            self.target_wp_longitude_deg = 0.0

        elif cur_step["command"] == "go_to_waypoint":
            # print("Processing waypoint command")
            self.jsbsim["ap/heading_hold"] = True
            self.jsbsim["ap/heading-setpoint-select"] = 1
            self.jsbsim["guidance/target_wp_latitude_rad"] = np.radians(
                cur_step["waypoint"]["latitude_deg"]
            )
            self.jsbsim["guidance/target_wp_longitude_rad"] = np.radians(
                cur_step["waypoint"]["longitude_deg"]
            )
            self.jsbsim["ap/altitude_hold"] = True
            self.jsbsim["ap/altitude_setpoint"] = cur_step["waypoint"]["altitude_ft"]

            # Set output autopilot target info for PFD
            self.target_altitude_ft = cur_step["waypoint"]["altitude_ft"]
            self.target_wp_active = True
            self.target_wp_latitude_deg = cur_step["waypoint"]["latitude_deg"]
            self.target_wp_longitude_deg = cur_step["waypoint"]["longitude_deg"]

        elif cur_step["command"] == "land":
            # print("Processing land command")
            self.jsbsim["ap/heading_hold"] = True
            self.jsbsim["ap/heading_setpoint"] = np.degrees(
                self.attitude_heading_true_rad
            )
            self.jsbsim["ap/heading-setpoint-select"] = 0
            self.jsbsim["ap/altitude_hold"] = True
            self.jsbsim["ap/altitude_setpoint"] = 0.0

            # Set output autopilot target info for PFD
            self.target_altitude_ft = 0.0
            self.target_wp_active = False
            self.target_wp_latitude_deg = 0.0
            self.target_wp_longitude_deg = 0.0

            # Cut throttle when landing gear is down
            # TODO Judge landing based on WOW instead of at landing gear down
            if self.flight_control_command.landing_gear_cmd == 1.0:
                self.flight_control_command.power_cmd[0] = 0.0

    def check_completion_criteria(self, cur_step) -> bool:
        # Check for step completion criteria to increment to the next step
        is_cur_step_complete = False
        criteria_param, criteria_comparator, criteria_thresh = cur_step[
            "completion_criteria"
        ]
        if criteria_param == "altitude_ft":
            criteria_var = self.position_h_sl_ft
        elif criteria_param == "distance_ft":
            criteria_var = meters_to_feet(
                haversine_distance_meters(
                    np.degrees(self.position_lat_geod_rad),
                    np.degrees(self.position_long_gc_rad),
                    cur_step["waypoint"]["latitude_deg"],
                    cur_step["waypoint"]["longitude_deg"],
                )
            )
        elif criteria_param == "velocity_kts":
            criteria_var = self.velocities_ve_kts
        else:
            print(
                f"WARNING: Unsupported completion criteria parameter: {criteria_param}"
            )

        if criteria_comparator == "<":
            is_cur_step_complete = criteria_var < criteria_thresh
        elif criteria_comparator == "<=":
            is_cur_step_complete = criteria_var <= criteria_thresh
        elif criteria_comparator == ">":
            is_cur_step_complete = criteria_var > criteria_thresh
        elif criteria_comparator == ">=":
            is_cur_step_complete = criteria_var >= criteria_thresh
        elif criteria_comparator == "==":
            is_cur_step_complete = criteria_var == criteria_thresh
        else:
            print(
                f"WARNING: Unsupported completion criteria comparator: {criteria_comparator}"
            )

        if not is_cur_step_complete:
            print(
                f"[ Running flight plan step {self.flight_plan_step}: {cur_step['command']}, "
                f"completion parameter {criteria_param}: {criteria_var:.0f}, criteria: {criteria_comparator}{criteria_thresh:.0f} ]",
                end="\r",
            )

        return is_cur_step_complete

    # ---------------------------------------------------------------------

    def enter_initialization_mode(self):
        if len(self.jsbsim_root_dir) > 0:
            root_dir = self.jsbsim_root_dir
            print(f"Checking for JSBSim root dir as an absolute path: {root_dir}")
            if not os.path.isdir(root_dir) and self.aerosim_root_path is not None:
                # If the root dir is not found, check if it is relative to the AeroSim root dir
                root_dir = os.path.join(self.aerosim_root_path, self.jsbsim_root_dir)
                print(
                    f"Checking for JSBSim root dir relative to AeroSim root dir: {root_dir}"
                )
            if not os.path.isdir(root_dir):
                # If the root dir is still not found, check if it is relative to the working dir
                working_dir = os.getcwd()
                root_dir = os.path.join(working_dir, self.jsbsim_root_dir)
                print(
                    f"Checking for JSBSim root dir relative to working dir: {root_dir}"
                )
        else:
            root_dir = jsbsim.get_default_root_dir()

        abs_root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(abs_root_dir):
            print(f"ERROR: JSBSim root dir not found: {abs_root_dir}")
            return

        print(f"JSBSim root dir set to: {abs_root_dir}")
        print(f"Initializing JSBSim for config: {self.jsbsim_script}")
        self.jsbsim = jsbsim.FGFDMExec(abs_root_dir)
        self.jsbsim.load_script(self.jsbsim_script)
        print(f"JSBSim dt={self.jsbsim.get_delta_t()}")
        self.jsbsim.run_ic()
        # self.jsbsim.print_simulation_configuration()
        # self.fdm.set_dt(self.dt_sec)

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time, step_size) -> bool:
        # print(f"do_step. t={current_time:.6f} step_size={step_size:.6f}")
        if self.jsbsim is None:
            print("ERROR: JSBSim not initialized.")
            return False

        # Do time step calcs
        step_ok = True
        end_time = current_time + step_size
        self.time = self.jsbsim.get_sim_time()
        # print(f"start time={self.time:.6f}")

        # Write inputs to JSBSim
        self.get_inputs_from_aerosim()

        # Step JSBSim until the FMU step end time
        while self.time < end_time:
            step_ok = self.jsbsim.run()
            self.time = self.jsbsim.get_sim_time()
            if not step_ok:
                print(f"WARNING: JSBSim step terminated at time={self.time:.6f}")
                break

        # Read outputs from JSBSim
        self.set_outputs_to_aerosim()

        # print(f"FMU end time = {end_time:.6f}, jsbsim_time={jsbsim_time:.6f}")
        return True

    def terminate(self):
        print("Terminating JSBSim autopilot controller model.")
        self.jsbsim = None
        self.time = 0.0
