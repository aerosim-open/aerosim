from aerosim_core import (
    feet_to_meters,
    register_fmu3_var,
    register_fmu3_param,
    lla_to_ned,
)

from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import os
import numpy as np
import math
import jsbsim
from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave

class takeoff_fmu(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jsbsim = None

        self.orig_lat = 0.0
        self.orig_lon = 0.0
        self.init_heading = 0

        register_fmu3_param(self, "orig_lat")
        register_fmu3_param(self, "orig_lon")
        register_fmu3_param(self, "init_heading")

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # Define Aerosim interface output variables
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="output")

    def set_outputs_to_aerosim(self):
        if self.jsbsim is None:
            return

        ned = lla_to_ned(
            self.jsbsim["position/lat-geod-deg"],
            self.jsbsim["position/long-gc-deg"],
            self.jsbsim["position/h-sl-meters"],
            self.orig_lat,
            self.orig_lon,
            0.0,  # Use zero altitude as the origin for NED frame to output height as h-sl-meters
        )

        self.vehicle_state.state.pose.position.x = ned[0]
        self.vehicle_state.state.pose.position.y = ned[1]
        self.vehicle_state.state.pose.position.z = ned[2]

        roll = self.jsbsim["attitude/phi-rad"]
        pitch = self.jsbsim["attitude/theta-rad"]
        yaw = self.jsbsim["attitude/psi-rad"]
        two_pi = 2.0 * math.pi
        yaw = (yaw + two_pi) % two_pi  # Convert to 0-2pi range

        rotation = Rotation.from_euler("zyx", [roll, pitch, yaw])
        q_w, q_x, q_y, q_z = rotation.as_quat(scalar_first=True)
        self.vehicle_state.state.pose.orientation.w = q_w
        self.vehicle_state.state.pose.orientation.x = q_x
        self.vehicle_state.state.pose.orientation.y = q_y
        self.vehicle_state.state.pose.orientation.z = q_z

        self.vehicle_state.velocity.x = feet_to_meters(self.jsbsim["velocities/u-fps"])
        self.vehicle_state.velocity.y = feet_to_meters(self.jsbsim["velocities/v-fps"])
        self.vehicle_state.velocity.z = feet_to_meters(self.jsbsim["velocities/w-fps"])

        self.vehicle_state.angular_velocity.x = self.jsbsim["velocities/p-rad_sec"]
        self.vehicle_state.angular_velocity.y = self.jsbsim["velocities/q-rad_sec"]
        self.vehicle_state.angular_velocity.z = self.jsbsim["velocities/r-rad_sec"]

        self.vehicle_state.acceleration.x = feet_to_meters(
            self.jsbsim["accelerations/udot-ft_sec2"]
        )
        self.vehicle_state.acceleration.y = feet_to_meters(
            self.jsbsim["accelerations/vdot-ft_sec2"]
        )
        self.vehicle_state.acceleration.z = feet_to_meters(
            self.jsbsim["accelerations/wdot-ft_sec2"]
        )

        self.vehicle_state.angular_acceleration.x = self.jsbsim[
            "accelerations/pdot-rad_sec2"
        ]
        self.vehicle_state.angular_acceleration.y = self.jsbsim[
            "accelerations/qdot-rad_sec2"
        ]
        self.vehicle_state.angular_acceleration.z = self.jsbsim[
            "accelerations/rdot-rad_sec2"
        ]


    def enter_initialization_mode(self):

        self.jsbsim = jsbsim.FGFDMExec(jsbsim.get_default_root_dir())
        self.jsbsim.load_model('c172r')

        self.jsbsim['ic/h-sl-ft'] = 0      # Initial altitude (Sea Level)
        self.jsbsim['ic/u-fps'] = 0        # Initial velocity (Stationary)
        self.jsbsim['ic/vc-rad_sec'] = 0   # No initial pitch rotation

        self.jsbsim['ic/h-agl-ft'] = 4.43 # Wheels might be below ground, might want to let aircraft drop

        self.jsbsim['ic/lat-geod-deg'] = self.orig_lat  # Approximate latitude
        self.jsbsim['ic/long-gc-deg'] = self.orig_lon  # Approximate longitude
        self.jsbsim['ic/psi-true-deg'] = self.init_heading  # Facing East
        self.jsbsim['ic/gamma-deg'] = 0     # No initial climb angle
        self.jsbsim.run_ic()  # Apply initial conditions
        
        # Start the engine
        self.jsbsim[f"fcs/mixture-cmd-norm"] = 1.0
        self.jsbsim[f"fcs/advance-cmd-norm"] = 1.0
        self.jsbsim[f"propulsion/magneto_cmd"] = 3
        self.jsbsim[f"propulsion/starter_cmd"] = 1
        
        # Release the brakes and set flaps for takeoff
        self.jsbsim["fcs/center-brake-cmd-norm"] = 0
        self.jsbsim["fcs/left-brake-cmd-norm"] = 0
        self.jsbsim["fcs/right-brake-cmd-norm"] = 0
        self.jsbsim["fcs/flap-pos-deg"] = 25


    def exit_initialization_mode(self):
        pass

    def hold_altitude(self, target_altitude, target_speed):

        # # PID Controller Parameters
        Kp = 0.005  # Proportional gain
        Kp_throttle = 0.01  # Proportional gain
        Ki = 0.0001  # Integral gain
        Kd = 0.01  # Derivative gain

        current_altitude = self.jsbsim['position/h-agl-ft']
        current_speed = self.jsbsim['velocities/vc-kts']

        # Compute altitude error
        altitude_error = target_altitude - current_altitude

        # Adjust elevator
        elevator_command = Kp * altitude_error
        elevator_command = max(-0.1, min(0.1, elevator_command))
        self.jsbsim['fcs/elevator-cmd-norm'] = - elevator_command

        # Adjust throttle based on airspeed
        speed_error = target_speed - current_speed
        throttle_command = 0.75 + Kp_throttle * speed_error  # Base throttle + correction
        throttle_command = max(0, min(1, throttle_command))  # Limit between 0 and 1
        self.jsbsim['fcs/throttle-cmd-norm'] = throttle_command

    def do_step(self, current_time: float, step_size: float) -> bool:

        # Do time step calcs
        step_ok = True
        end_time = current_time + step_size
        self.time = self.jsbsim.get_sim_time()

        self.jsbsim['fcs/throttle-cmd-norm'] = 1.0

        self.jsbsim['fcs/aileron-cmd-norm'] = - 5.0 * self.jsbsim['attitude/roll-rad']


        if self.jsbsim['position/h-agl-ft'] > 50:
            self.hold_altitude(100, 80)
        elif self.jsbsim['velocities/vc-kts'] > 65:
            self.jsbsim["fcs/elevator-cmd-norm"] = -0.3

        self.jsbsim.run()

        print(f"JSB Time: {self.jsbsim.get_sim_time():.2f}, Vcal: {self.jsbsim['velocities/vc-kts']:.2f}, Alt: {self.jsbsim['position/h-agl-ft']:.2f} ft, Throttle: {self.jsbsim['fcs/throttle-cmd-norm'] :.2f}, Elv: {self.jsbsim['fcs/elevator-cmd-norm'] :.2f}")

        self.set_outputs_to_aerosim()

        return True
        










        