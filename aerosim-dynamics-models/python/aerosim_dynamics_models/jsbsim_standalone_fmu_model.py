from aerosim_core import (
    feet_to_meters,
    register_fmu3_var,
    register_fmu3_param,
    lla_to_ned,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import os
import math
import jsbsim
from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class jsbsim_standalone_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.aerosim_root_path = os.getenv("AEROSIM_ROOT")
        self.jsbsim = None
        self.orig_lat = 0.0
        self.orig_lon = 0.0

        # ---------------------------------------------------------------------

        # Define Aerosim interface input variables
        # (Running JSBSim as a standalone scripted FDM, so no inputs are applied)

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="output")

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = "Implementation of a JSBSim fixed-wing dynamics model"

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define JSBSim-specific auxiliary parameters

        self.jsbsim_root_dir = ""
        self.jsbsim_script = "scripts/c3104_dynamics.xml"

        register_fmu3_param(self, "jsbsim_root_dir")
        register_fmu3_param(self, "jsbsim_script")

        # ---------------------------------------------------------------------

    # Map implementation variables to interface variables
    def get_inputs_from_aerosim(self):
        # (Running JSBSim as a standalone scripted FDM, so no inputs are applied)
        pass

    def set_outputs_to_aerosim(self):
        if self.jsbsim is None:
            return

        # Copy outputs from the JSBSim FDM to the Aerosim interface variables

        ned = lla_to_ned(
            self.jsbsim["position/lat-geod-deg"],
            self.jsbsim["position/long-gc-deg"],
            self.jsbsim["position/h-sl-meters"],
            self.orig_lat,
            self.orig_lon,
            0.0,  # Use zero altitude as the origin for NED frame to output height as h-sl-meters
        )

        # Position in world NED frame
        self.vehicle_state.state.pose.position.x = ned[0]
        self.vehicle_state.state.pose.position.y = ned[1]
        self.vehicle_state.state.pose.position.z = ned[2]

        roll = self.jsbsim["attitude/phi-rad"]
        pitch = self.jsbsim["attitude/theta-rad"]
        yaw = self.jsbsim["attitude/psi-rad"]
        two_pi = 2.0 * math.pi
        yaw = (yaw + two_pi) % two_pi  # Convert to 0-2pi range

        # Orientation in world NED frame
        rotation = Rotation.from_euler("zyx", [roll, pitch, yaw])
        q_w, q_x, q_y, q_z = rotation.as_quat(scalar_first=True)
        self.vehicle_state.state.pose.orientation.w = q_w
        self.vehicle_state.state.pose.orientation.x = q_x
        self.vehicle_state.state.pose.orientation.y = q_y
        self.vehicle_state.state.pose.orientation.z = q_z

        # Linear velocities in world NED frame
        self.vehicle_state.velocity.x = feet_to_meters(
            self.jsbsim["velocities/v-north-fps"]
        )
        self.vehicle_state.velocity.y = feet_to_meters(
            self.jsbsim["velocities/v-east-fps"]
        )
        self.vehicle_state.velocity.z = feet_to_meters(
            self.jsbsim["velocities/v-down-fps"]
        )

        # Linear velocities in body frame
        # self.vehicle_state.velocity.x = feet_to_meters(self.jsbsim["velocities/u-fps"])
        # self.vehicle_state.velocity.y = feet_to_meters(self.jsbsim["velocities/v-fps"])
        # self.vehicle_state.velocity.z = feet_to_meters(self.jsbsim["velocities/w-fps"])

        # Angular velocities in body frame
        self.vehicle_state.angular_velocity.x = self.jsbsim["velocities/p-rad_sec"]
        self.vehicle_state.angular_velocity.y = self.jsbsim["velocities/q-rad_sec"]
        self.vehicle_state.angular_velocity.z = self.jsbsim["velocities/r-rad_sec"]

        # Linear accelerations in body frame
        self.vehicle_state.acceleration.x = feet_to_meters(
            self.jsbsim["accelerations/udot-ft_sec2"]
        )
        self.vehicle_state.acceleration.y = feet_to_meters(
            self.jsbsim["accelerations/vdot-ft_sec2"]
        )
        self.vehicle_state.acceleration.z = feet_to_meters(
            self.jsbsim["accelerations/wdot-ft_sec2"]
        )

        # Angular accelerations in body frame
        self.vehicle_state.angular_acceleration.x = self.jsbsim[
            "accelerations/pdot-rad_sec2"
        ]
        self.vehicle_state.angular_acceleration.y = self.jsbsim[
            "accelerations/qdot-rad_sec2"
        ]
        self.vehicle_state.angular_acceleration.z = self.jsbsim[
            "accelerations/rdot-rad_sec2"
        ]

        # print(
        #     f"JSBSim t={self.time:.0f} pos=({self.vehicle_state.state.pose.position.x:.0f}, {self.vehicle_state.state.pose.position.y:.0f}, {self.vehicle_state.state.pose.position.z:.0f}), roll={roll*180/math.pi:.0f}, pitch={pitch*180/math.pi:.0f}, yaw={yaw*180/math.pi:.0f}"
        # )

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
        # self.fdm.set_dt(self.dt_sec)
        print(f"JSBSim dt={self.jsbsim.get_delta_t()}")
        self.jsbsim.run_ic()
        # self.jsbsim.print_simulation_configuration()
        # self.jsbsim.print_property_catalog()

        self.orig_lat = self.jsbsim["ic/lat-geod-deg"]
        self.orig_lon = self.jsbsim["ic/long-gc-deg"]
        print(f"JSBSim origin lla=({self.orig_lat:.6f}, {self.orig_lon:.6f})")

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
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

        # print(f"FMU end time = {end_time:.6f}, time={self.time:.6f}")
        return True

    def terminate(self):
        print("Terminating JSBSim standalone model.")
        self.jsbsim = None
        self.time = 0.0
