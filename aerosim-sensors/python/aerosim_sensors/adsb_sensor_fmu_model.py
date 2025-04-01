from aerosim_core import register_fmu3_var, register_fmu3_param, ned_to_lla
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace
from aerosim_sensors import adsb_functions
import math
from scipy.spatial.transform import Rotation
from pythonfmu3 import Fmi3Slave

# Note: The class name is used as the FMU file name
class adsb_sensor_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---------------------------------------------------------------------
        # FMU general variables
        self.author = "AeroSim"
        self.description = "ADS-B Sensor from Vehicle State Publish Model"
        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="input")
        # ---------------------------------------------------------------------
        self.adsb = adsb_functions.adsb_from_gnss_data(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0
        )
        self.adsb = dict_to_namespace(self.adsb.to_dict())
        register_fmu3_var(self, "adsb", causality="output")
        # ---------------------------------------------------------------------

        self.world_origin_latitude = 0.0
        register_fmu3_param(self, "world_origin_latitude")
        self.world_origin_longitude = 0.0
        register_fmu3_param(self, "world_origin_longitude")
        self.world_origin_altitude = 0.0
        register_fmu3_param(self, "world_origin_altitude")
        # ---------------------------------------------------------------------
        self.last_velocity_mag: float = 0.0

    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
        self.time = current_time + step_size
        self._update_adsb(step_size)
        return True

    def terminate(self):
        print("Terminating ADS-B Sensor from Vehicle State Publish Model")
        self.time = 0.0

    def _update_adsb(self, dt: float):
        pose = self.vehicle_state.state.pose
        position = pose.position
        velocity = self.vehicle_state.velocity

        q = pose.orientation
        if q.w == 0.0 and q.x == 0.0 and q.y == 0.0 and q.z == 0.0:
            q.w = 1.0
        quat = [q.x, q.y, q.z, q.w]
        rot = Rotation.from_quat(quat)
        euler_angles = rot.as_euler('zyx', degrees=True)

        (latitude, longitude, altitude) = ned_to_lla(
            position.x, position.y, position.z,
            self.world_origin_latitude,
            self.world_origin_longitude,
            self.world_origin_altitude
        )

        velocity_n = velocity.x
        velocity_e = velocity.y
        velocity_d = velocity.z
        velocity_total = math.sqrt(velocity_n ** 2 + velocity_e ** 2 + velocity_d ** 2)
        acceleration = (velocity_total - self.last_velocity_mag) / dt
        self.last_velocity_mag = velocity_total

        self.adsb.message.latitude = latitude
        self.adsb.message.longitude = longitude
        self.adsb.message.altitude = altitude
        self.adsb.message.velocity = velocity_total
        self.adsb.message.heading = euler_angles[2] # Yaw
        self.adsb.message.ground_speed = math.sqrt(velocity_n ** 2 + velocity_e ** 2)
        self.adsb.message.acceleration = acceleration
