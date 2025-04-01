from aerosim_core import (
    register_fmu3_var,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import math
from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave


class effector:
    def __init__(self, name, type, direction, offset_deg):
        # Set effector properties
        self.effector_name = name  # Name of effector
        self.effector_type = type  # Type of effector
        self.effector_offset_deg = offset_deg  # Rotation offset in degree

        # Set effector persistent variables
        self.roll_deg = 0.0  # Effector roll in degree
        self.pitch_deg = 0.0  # Effector pitch in degree
        self.yaw_deg = 0.0  # Effector yaw in degree

        # Create effector state
        self.effector_state = dict_to_namespace(aerosim_types.EffectorState().to_dict())

        # Position of an effector on an eVTOL does not change
        self.effector_state.pose.position.x = 0.0
        self.effector_state.pose.position.y = 0.0
        self.effector_state.pose.position.z = 0.0

        # Multiply direction of rotation and convert D2R
        self.direction_and_d2r = direction * math.pi / 180.0

    def do_step(
        self, dt_s: float, tilt_deg: float, proprotor_rpm: float, liftrotor_rpm: float
    ):
        # Calculate conversion variables
        rpm_to_deg = (
            dt_s * 6.0
        )  # Convert RPM to degree of rotation in 'dt_s' time duration (RPM/60.0*dt_s*360)

        # Calculate orientation based on effector_type
        if self.effector_type == "tiltrotor":
            self.pitch_deg = (
                tilt_deg + self.effector_offset_deg
            ) * self.direction_and_d2r
        elif self.effector_type == "proprotor":
            self.yaw_deg += (proprotor_rpm * rpm_to_deg) * self.direction_and_d2r
            self.yaw_deg = (
                self.yaw_deg + math.tau
            ) % math.tau  # Convert to 0-2pi range
        elif self.effector_type == "liftrotor":
            self.yaw_deg += (liftrotor_rpm * rpm_to_deg) * self.direction_and_d2r
            self.yaw_deg = (
                self.yaw_deg + math.tau
            ) % math.tau  # Convert to 0-2pi range

        # Convert RPY to Quaternion
        rotation = Rotation.from_euler(
            "zyx", [self.roll_deg, self.pitch_deg, self.yaw_deg]
        )
        q_w, q_x, q_y, q_z = rotation.as_quat(scalar_first=True)
        self.effector_state.pose.orientation.w = q_w
        self.effector_state.pose.orientation.x = q_x
        self.effector_state.pose.orientation.y = q_y
        self.effector_state.pose.orientation.z = q_z


# Note: The class name is used as the FMU file name
class evtol_effectors_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---------------------------------------------------------------------

        # Create effector dictionary and populate with effector objects
        self.effector_dict = {}

        # Outer right tiltrotor
        self.effector_dict["tiltrotor_1"] = effector(
            "tiltrotor_1", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_1"] = effector("rotor_1", "proprotor", 1.0, 0.0)

        # Outer left tiltrotor
        self.effector_dict["tiltrotor_2"] = effector(
            "tiltrotor_2", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_2"] = effector("rotor_2", "proprotor", -1.0, 0.0)

        # Inner front left tiltrotor
        self.effector_dict["tiltrotor_3"] = effector(
            "tiltrotor_3", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_3"] = effector("rotor_3", "proprotor", -1.0, 0.0)

        # Inner rear right tiltrotor
        self.effector_dict["tiltrotor_4"] = effector(
            "tiltrotor_4", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_4"] = effector("rotor_4", "proprotor", -1.0, 0.0)

        # Inner front right tiltrotor
        self.effector_dict["tiltrotor_5"] = effector(
            "tiltrotor_5", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_5"] = effector("rotor_5", "proprotor", 1.0, 0.0)

        # Inner rear left tiltrotor
        self.effector_dict["tiltrotor_6"] = effector(
            "tiltrotor_6", "tiltrotor", -1.0, 0.0
        )
        self.effector_dict["rotor_6"] = effector("rotor_6", "proprotor", 1.0, 0.0)

        # ---------------------------------------------------------------------

        # Define Aerosim interface input variables

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables

        self.tiltrotor_1 = self.effector_dict["tiltrotor_1"].effector_state
        register_fmu3_var(self, "tiltrotor_1", causality="output")
        self.rotor_1 = self.effector_dict["rotor_1"].effector_state
        register_fmu3_var(self, "rotor_1", causality="output")

        self.tiltrotor_2 = self.effector_dict["tiltrotor_2"].effector_state
        register_fmu3_var(self, "tiltrotor_2", causality="output")
        self.rotor_2 = self.effector_dict["rotor_2"].effector_state
        register_fmu3_var(self, "rotor_2", causality="output")

        self.tiltrotor_3 = self.effector_dict["tiltrotor_3"].effector_state
        register_fmu3_var(self, "tiltrotor_3", causality="output")
        self.rotor_3 = self.effector_dict["rotor_3"].effector_state
        register_fmu3_var(self, "rotor_3", causality="output")

        self.tiltrotor_4 = self.effector_dict["tiltrotor_4"].effector_state
        register_fmu3_var(self, "tiltrotor_4", causality="output")
        self.rotor_4 = self.effector_dict["rotor_4"].effector_state
        register_fmu3_var(self, "rotor_4", causality="output")

        self.tiltrotor_5 = self.effector_dict["tiltrotor_5"].effector_state
        register_fmu3_var(self, "tiltrotor_5", causality="output")
        self.rotor_5 = self.effector_dict["rotor_5"].effector_state
        register_fmu3_var(self, "rotor_5", causality="output")

        self.tiltrotor_6 = self.effector_dict["tiltrotor_6"].effector_state
        register_fmu3_var(self, "tiltrotor_6", causality="output")
        self.rotor_6 = self.effector_dict["rotor_6"].effector_state
        register_fmu3_var(self, "rotor_6", causality="output")

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = "Implementation of an eVTOL effector model"

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define evtol-effector-specific auxiliary parameters
        self.tilt_deg = 0.0
        self.proprotor_rpm = 0.0
        self.liftrotor_rpm = 0.0
        register_fmu3_var(self, "tilt_deg", causality="input")
        register_fmu3_var(self, "proprotor_rpm", causality="input")
        register_fmu3_var(self, "liftrotor_rpm", causality="input")

        # ---------------------------------------------------------------------

    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
        # Do time step calcs
        dt_s = (current_time + step_size) - self.time
        self.time = current_time + step_size

        # Step effectors
        self.effector_dict["tiltrotor_1"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_1"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        self.effector_dict["tiltrotor_2"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_2"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        self.effector_dict["tiltrotor_3"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_3"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        self.effector_dict["tiltrotor_4"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_4"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        self.effector_dict["tiltrotor_5"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_5"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        self.effector_dict["tiltrotor_6"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )
        self.effector_dict["rotor_6"].do_step(
            dt_s, self.tilt_deg, self.proprotor_rpm, self.liftrotor_rpm
        )

        return True

    def terminate(self):
        print("Terminating eVTOL effector model")
