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

class dynamics_fmu(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jsbsim = None

        self.orig_lat = 0.0
        self.orig_lon = 0.0
        self.init_heading = 0

        register_fmu3_param(self, "orig_lat")
        register_fmu3_param(self, "orig_lon")
        register_fmu3_param(self, "init_heading")

        self.jsbsim_root_dir = ""
        self.jsbsim_script = "c172"

        # FMU variables to feed back to the autopilot
        self.vcal_knts = 0.0
        self.agl_ft = 0.0
        self.roll_rad = 0.0
        self.pitch_rad = 0.0
        self.psi_rad = 0.0
        self.lat = 0.0
        self.lon = 0.0

        register_fmu3_var(self, "vcal_knts", causality="output")
        register_fmu3_var(self, "agl_ft", causality="output")
        register_fmu3_var(self, "roll_rad", causality="output")
        register_fmu3_var(self, "pitch_rad", causality="output")
        register_fmu3_var(self, "psi_rad", causality="output")
        register_fmu3_var(self, "lat", causality="output")
        register_fmu3_var(self, "lon", causality="output")

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # Define Aerosim interface output variables
        # VehicleState
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="output")

        # Define AeroSim interface input variables
        # FlightControlCommand
        self.flight_control_command = dict_to_namespace(
            aerosim_types.FlightControlCommand().to_dict()
        )
        self.flight_control_command.power_cmd = np.array([0.0])
        register_fmu3_var(self, "flight_control_command", causality="input")

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

        # Initialize the JSBSim Cessna 172R model
        self.jsbsim = jsbsim.FGFDMExec(jsbsim.get_default_root_dir());
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

    def do_step(self, current_time: float, step_size: float) -> bool:

        self.time = self.jsbsim.get_sim_time()

        print('Flap position: ' + str(self.jsbsim['fcs/flap-pos-deg']))

        # Set the flight controls from the incoming FlightControlCommand message
        self.jsbsim['fcs/throttle-cmd-norm'] = self.flight_control_command.power_cmd
        self.jsbsim['fcs/aileron-cmd-norm'] = self.flight_control_command.roll_cmd
        self.jsbsim['fcs/elevator-cmd-norm'] = self.flight_control_command.pitch_cmd
        self.jsbsim['fcs/flap-pos-deg'] = self.flight_control_command.flap_cmd * 25

        # Step JSBSim
        self.jsbsim.run()

        # Update the FMU output variables with the new position, attitude and speed
        self.vcal_knts = self.jsbsim['velocities/vc-kts']
        self.agl_ft = self.jsbsim['position/h-agl-ft']
        self.roll_rad = self.jsbsim['attitude/roll-rad']
        self.pitch_rad = self.jsbsim['attitude/pitch-rad']
        self.psi_rad = self.jsbsim['attitude/psi-rad']
        self.lat = self.jsbsim['position/lat-geod-deg']
        self.lon = self.jsbsim['position/long-gc-deg']

        # Translate the JSBSim data to the AeroSim VehicleState type for the renderer
        self.set_outputs_to_aerosim()

        return True
        










        