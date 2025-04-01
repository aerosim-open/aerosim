from aerosim_core import (
    register_fmu3_var,
    register_fmu3_param,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import math
from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class rotor_effector_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        # ---------------------------------------------------------------------

        # Define Aerosim interface input variables

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables
        self.effector_state = dict_to_namespace(aerosim_types.EffectorState().to_dict())
        register_fmu3_var(self, "effector_state", causality="output")

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = "Implementation of a rotor (rotate or tilt) effector model"

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define rotor-effector-specific auxiliary parameters
        self.effector_type = ""
        self.rotation_direction = 0.0
        self.rotation_scale = 1.0
        self.rotation_offset_deg = 0.0
        self.rotation_axis = "yaw"
        register_fmu3_param(self, "effector_type")
        register_fmu3_param(self, "rotation_direction")
        register_fmu3_param(self, "rotation_scale")
        register_fmu3_param(self, "rotation_offset_deg")
        register_fmu3_param(self, "rotation_axis")

        self.tilt_deg = 0.0
        self.proprotor_rpm = 0.0
        register_fmu3_var(self, "tilt_deg", causality="input")
        register_fmu3_var(self, "proprotor_rpm", causality="input")

        # ---------------------------------------------------------------------

    def enter_initialization_mode(self):
        # Position of a rotor effector does not change
        self.effector_state.pose.position.x = 0.0
        self.effector_state.pose.position.y = 0.0
        self.effector_state.pose.position.z = 0.0

        # Multiply direction of rotation and convert degree-to-radians
        self.direction_and_deg2rad = self.rotation_direction * math.pi / 180.0

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
        # Do time step calcs
        dt_s = (current_time + step_size) - self.time
        self.time = current_time + step_size

        # Calculate conversion variables
        rpm_to_deg = (
            dt_s * 6.0
        )  # Convert RPM to degree of rotation in 'dt_s' time duration (RPM/60.0*dt_s*360)

        # Calculate orientation based on effector_type
        if self.effector_type == "tiltrotor":
            self.pitch = (
                (self.tilt_deg + self.rotation_offset_deg)
                * self.direction_and_deg2rad
                * self.rotation_scale
            )
        elif self.effector_type == "proprotor":
            if self.rotation_axis == "yaw":
                self.yaw += (
                    (self.proprotor_rpm * rpm_to_deg)
                    * self.direction_and_deg2rad
                    * self.rotation_scale
                )
                self.yaw = (self.yaw + math.tau) % math.tau  # Convert to 0-2pi range
            elif self.rotation_axis == "roll":
                self.roll += (
                    (self.proprotor_rpm * rpm_to_deg)
                    * self.direction_and_deg2rad
                    * self.rotation_scale
                )
                self.roll = (self.roll + math.tau) % math.tau  # Convert to 0-2pi range
            elif self.rotation_axis == "pitch":
                self.pitch += (
                    (self.proprotor_rpm * rpm_to_deg)
                    * self.direction_and_deg2rad
                    * self.rotation_scale
                )
                self.pitch = (
                    self.pitch + math.tau
                ) % math.tau  # Convert to 0-2pi range

        # Convert RPY to Quaternion
        rotation = Rotation.from_euler("zyx", [self.roll, self.pitch, self.yaw])
        q_w, q_x, q_y, q_z = rotation.as_quat(scalar_first=True)
        self.effector_state.pose.orientation.w = q_w
        self.effector_state.pose.orientation.x = q_x
        self.effector_state.pose.orientation.y = q_y
        self.effector_state.pose.orientation.z = q_z

        return True

    def terminate(self):
        print("Terminating rotor effector model")
