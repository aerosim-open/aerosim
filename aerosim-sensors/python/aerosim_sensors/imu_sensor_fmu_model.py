from typing import Tuple
from aerosim_core import register_fmu3_var, register_fmu3_param
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace
from aerosim_data import middleware
from aerosim_sensors import IMU

from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class imu_sensor_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---------------------------------------------------------------------
        self.vehicle_state = dict_to_namespace(
            aerosim_types.VehicleState().to_dict()
        )
        register_fmu3_var(self, "vehicle_state", causality="input")
        # ---------------------------------------------------------------------
        self.imu = dict_to_namespace(
            aerosim_types.IMU().to_dict()
        )
        register_fmu3_var(self, "imu", causality="output")
        # ---------------------------------------------------------------------
        # FMU general variables
        self.author = "AeroSim"
        self.description = "IMU Sensor Publish Model"
        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")
        # ---------------------------------------------------------------------
        self.world_origin_latitude = 0.0
        register_fmu3_param(self, "world_origin_latitude")
        self.world_origin_longitude = 0.0
        register_fmu3_param(self, "world_origin_longitude")
        self.world_origin_altitude = 0.0
        register_fmu3_param(self, "world_origin_altitude")
        # ---------------------------------------------------------------------
        self.last_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.last_rot: Rotation = Rotation.from_quat([0.0, 0.0, 0.0, 1.0])
        self.last_magnetic_field: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
        # Update the time variable
        self.time = current_time + step_size
        self._update_imu(step_size)
        return True

    def terminate(self):
        print("Terminating imu Sensor Publish Model")
        self.time = 0.0

    def _update_imu(self, dt: float):
        pose = self.vehicle_state.state.pose
        velocity = self.vehicle_state.velocity
        q = pose.orientation
        if q.w == 0.0 and q.x == 0.0 and q.y == 0.0 and q.z == 0.0:
            q.w = 1.0
        quat = [q.x, q.y, q.z, q.w]
        current_rot = Rotation.from_quat(quat)

        acceleration = (
            (velocity.x - self.last_velocity[0]) / dt,
            (velocity.y - self.last_velocity[1]) / dt,
            (velocity.z - self.last_velocity[2]) / dt
        )
        delta_rot = current_rot * self.last_rot.inv()
        rotvec = delta_rot.as_rotvec()
        gyroscope = tuple(rotvec / dt)

        self.last_velocity = (velocity.x, velocity.y, velocity.z)
        self.last_rot = current_rot

        self.imu.acceleration.x = acceleration[0]
        self.imu.acceleration.y = acceleration[1]
        self.imu.acceleration.z = acceleration[2]

        self.imu.gyroscope.x = gyroscope[0]
        self.imu.gyroscope.y = gyroscope[1]
        self.imu.gyroscope.z = gyroscope[2]

