from aerosim_core import register_fmu3_var, register_fmu3_param
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import os
import math
import numpy as np
import jsbsim

from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class jsbsim_flight_controller_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.aerosim_root_path = os.getenv("AEROSIM_ROOT")
        self.jsbsim = None
        # JSBSIM_DEBUG: 0 = disable JSBSIM console output, 1 = normal output
        os.environ["JSBSIM_DEBUG"] = "0"

        # ---------------------------------------------------------------------

        # Define Aerosim interface input variables
        self.flight_control_command = dict_to_namespace(
            aerosim_types.FlightControlCommand().to_dict()
        )

        # Note: for array variables, need to set initial values as a numpy array and
        # define the dimensions for the number of elements to build into the FMU
        self.flight_control_command.power_cmd = np.array([0.0])

        register_fmu3_var(self, "flight_control_command", causality="input")

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables
        self.aircraft_effector_command = dict_to_namespace(
            aerosim_types.AircraftEffectorCommand().to_dict()
        )

        # Note: for array variables, need to set initial values as a numpy array and
        # define the dimensions for the number of elements to build into the FMU
        self.aircraft_effector_command.throttle_cmd = np.array([0.0, 0.0])
        self.aircraft_effector_command.aileron_cmd_angle_rad = np.array([0.0, 0.0])
        self.aircraft_effector_command.elevator_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.rudder_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.thrust_tilt_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.flap_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.speedbrake_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.landing_gear_cmd = np.array([1.0])
        self.aircraft_effector_command.wheel_steer_cmd_angle_rad = np.array([0.0])
        self.aircraft_effector_command.wheel_brake_cmd = np.array(
            [0.0, 0.0, 0.0]
        )  # center, left, right

        register_fmu3_var(self, "aircraft_effector_command", causality="output")

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = (
            "Implementation of a JSBSim fixed-wing flight controller model"
        )

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define JSBSim-specific auxiliary parameters

        self.jsbsim_root_dir = "jsbsim_xml/"
        self.jsbsim_script = "scripts/c3104_flight_controller.xml"
        self.max_wheel_steer_angle_deg = 30.0

        register_fmu3_param(self, "jsbsim_root_dir")
        register_fmu3_param(self, "jsbsim_script")
        register_fmu3_param(self, "max_wheel_steer_angle_deg")

        # ---------------------------------------------------------------------

    # Map implementation variables to interface variables
    def get_inputs_from_aerosim(self):
        # Copy inputs from the Aerosim interface variables to the JSBSim flight controller

        # Input pwr_cmd is directly converted to throttle_cmd outputs
        # in set_outputs_to_aerosim()

        # Input the principle axes commands
        self.jsbsim["fcs/aileron-cmd-norm"] = self.flight_control_command.roll_cmd
        self.jsbsim["fcs/elevator-cmd-norm"] = self.flight_control_command.pitch_cmd
        self.jsbsim["fcs/rudder-cmd-norm"] = self.flight_control_command.yaw_cmd

        # No handling of thrust_tilt_cmd in JSBSim flight controller

        # Input the flap_cmd directly
        self.jsbsim["fcs/flap-cmd-norm"] = self.flight_control_command.flap_cmd

        # No handling of speedbrake_cmd yet

        # Input landing_gear_cmd is directly converted to landing_gear_cmd output
        # in set_outputs_to_aerosim()

        # Input wheel_steer_cmd is directly converted to wheel_steer_cmd_angle_rad
        # in set_outputs_to_aerosim()

        # Input wheel_brake_cmd is directly converted to wheel_brake_cmd outputs
        # in set_outputs_to_aerosim()

    def set_outputs_to_aerosim(self):
        if self.jsbsim is None:
            return

        # Copy outputs from the JSBSim flight controller to the Aerosim interface variables

        # Pass through the input single power_cmd to the two throttle_cmd outputs
        for engine_idx in range(2):
            self.aircraft_effector_command.throttle_cmd[engine_idx] = (
                self.flight_control_command.power_cmd[0]
            )

        self.aircraft_effector_command.aileron_cmd_angle_rad[0] = self.jsbsim[
            "fcs/left-aileron-pos-rad"
        ]
        self.aircraft_effector_command.aileron_cmd_angle_rad[1] = self.jsbsim[
            "fcs/right-aileron-pos-rad"
        ]

        self.aircraft_effector_command.elevator_cmd_angle_rad[0] = self.jsbsim[
            "fcs/elevator-pos-rad"
        ]

        self.aircraft_effector_command.rudder_cmd_angle_rad[0] = self.jsbsim[
            "fcs/rudder-pos-rad"
        ]

        # No handling of thrust_tilt_cmd_angle_rad in JSBSim flight controller

        self.aircraft_effector_command.flap_cmd_angle_rad[0] = (
            self.jsbsim["fcs/flap-pos-deg"] * math.pi / 180.0
        )

        # No handling of speedbrake_cmd_angle_rad in JSBSim flight controller

        self.aircraft_effector_command.landing_gear_cmd[0] = (
            self.flight_control_command.landing_gear_cmd
        )

        # Convert the input wheel_steer_cmd to the wheel_steer_cmd_angle_rad output
        self.aircraft_effector_command.wheel_steer_cmd_angle_rad[0] = (
            self.flight_control_command.wheel_steer_cmd
            * self.max_wheel_steer_angle_deg
            * math.pi
            / 180.0
        )

        # Pass through the input wheel_brake_cmd to the three wheel_brake_cmd outputs
        for wheel_idx in range(3):
            self.aircraft_effector_command.wheel_brake_cmd[wheel_idx] = (
                self.flight_control_command.wheel_brake_cmd
            )

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
        print("Terminating JSBSim flight controller model.")
        self.jsbsim = None
        self.time = 0.0
