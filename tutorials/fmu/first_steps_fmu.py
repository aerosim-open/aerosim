from aerosim_core import (
    register_fmu3_var,
    register_fmu3_param,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

from pythonfmu3 import Fmi3Slave

import math
from scipy.spatial.transform import Rotation


class first_steps_fmu(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # -----------------------------------------------------------------------
        # Define FMU standard variables

        self.author = "AeroSim"
        self.description = "First steps tutorial FMU example"

        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # -----------------------------------------------------------------------
        # Define Aerosim interface output variables
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="output")

        # -----------------------------------------------------------------------
        # Define custom auxiliary variables

        self.custom_fmu_input = 0.0
        register_fmu3_var(self, "custom_fmu_input", causality="input")

        self.custom_fmu_output = 0.0
        register_fmu3_var(self, "custom_fmu_output", causality="output")

        # -----------------------------------------------------------------------
        # Define FMU parameters
        self.init_pos_north = 0.0
        register_fmu3_param(self, "init_pos_north")

        self.init_pos_east = 0.0
        register_fmu3_param(self, "init_pos_east")

        self.init_pos_down = 0.0
        register_fmu3_param(self, "init_pos_down")

    # Inherited enter_initialization_mode() callback from Fmi3Slave
    def enter_initialization_mode(self):
        """Initialize the start position"""
        self.vehicle_state.state.pose.position.x = self.init_pos_north
        self.vehicle_state.state.pose.position.y = self.init_pos_east
        self.vehicle_state.state.pose.position.z = self.init_pos_down

    # Inherited exit_initialization_mode callback from Fmi3Slave
    def exit_initialization_mode(self):
        pass

    # Inherited do_step() callback from Fmi3Slave
    def do_step(self, current_time: float, step_size: float) -> bool:
        """Simulation step execution"""
        self.time += step_size

        if self.vehicle_state.state.pose.position.z - self.init_pos_down > -10:
            self.vehicle_state.state.pose.position.z -= 0.02 # Move upwards in the world
        else:
            two_pi = 2.0 * math.pi
            yaw = (self.yaw/360 + two_pi) % two_pi  # Convert to 0-2pi range

            rotation = Rotation.from_euler("zyx", [0.0, 0.0, yaw])
            q_w, q_x, q_y, q_z = rotation.as_quat(scalar_first=True)

            self.vehicle_state.state.pose.orientation.w = q_w
            self.vehicle_state.state.pose.orientation.x = q_x
            self.vehicle_state.state.pose.orientation.y = q_y
            self.vehicle_state.state.pose.orientation.z = q_z

            self.yaw += 1

        return True

    # Inherited terminate() callback from Fmi3Slave
    def terminate(self):
        pass
