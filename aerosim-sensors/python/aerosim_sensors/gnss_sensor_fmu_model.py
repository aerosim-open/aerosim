from aerosim_core import register_fmu3_var, register_fmu3_param, ned_to_lla
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class gnss_sensor_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---------------------------------------------------------------------
        self.vehicle_state = dict_to_namespace(
            aerosim_types.VehicleState().to_dict()
        )
        register_fmu3_var(self, "vehicle_state", causality="input")
        # ---------------------------------------------------------------------
        self.gnss = dict_to_namespace(
            aerosim_types.GNSS().to_dict()
        )
        register_fmu3_var(self, "gnss", causality="output")
        # ---------------------------------------------------------------------
        # FMU general variables
        self.author = "AeroSim"
        self.description = "GNSS Sensor Publish Model"
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


    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time: float, step_size: float) -> bool:
        # Update the time variable
        self.time = current_time + step_size
        self._update_gnss()
        return True

    def terminate(self):
        print("Terminating GNSS Sensor Publish Model")
        self.time = 0.0

    def _update_gnss(self):
        pose = self.vehicle_state.state.pose
        (latitude, longitude, altitude) = ned_to_lla(
            pose.position.x, pose.position.y, pose.position.z, self.world_origin_latitude, self.world_origin_longitude, self.world_origin_altitude)

        q = pose.orientation
        if q.w == 0.0 and q.x == 0.0 and q.y == 0.0 and q.z == 0.0:
            q.w = 1.0
        quat = [q.x, q.y, q.z, q.w]
        rot = Rotation.from_quat(quat)
        euler_angles = rot.as_euler('zyx', degrees=True)

        self.gnss.latitude = latitude
        self.gnss.longitude = longitude
        self.gnss.altitude = altitude
        self.gnss.velocity.x = self.vehicle_state.velocity.x
        self.gnss.velocity.y = self.vehicle_state.velocity.y
        self.gnss.velocity.z = self.vehicle_state.velocity.z
        self.gnss.heading = euler_angles[2] # Yaw
