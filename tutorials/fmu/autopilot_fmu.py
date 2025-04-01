from aerosim_core import (
    feet_to_meters,
    register_fmu3_var,
    register_fmu3_param,
    haversine_distance_meters,
    lla_to_ned,
)

from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

import os
import json
import math
import jsbsim
import numpy as np
from scipy.spatial.transform import Rotation

from pythonfmu3 import Fmi3Slave

class autopilot_fmu(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Variables and filepaths for waypoints
        self.waypoints = None
        self.waypoints_dir = ''
        self.waypoints_file = ''
        self.current_waypoint = None

        register_fmu3_param(self, "waypoints_dir")
        register_fmu3_param(self, "waypoints_file")

        self.target_altitude = 150 # Feet
        self.target_speed = 100 # Knots

        register_fmu3_param(self, "target_altitude")
        register_fmu3_param(self, "target_speed")

        # Variables received from the flight dynamics FMU
        self.vcal_knts = 0.0
        self.agl_ft = 0.0
        self.roll_rad = 0.0
        self.pitch_rad = 0.0
        self.psi_rad = 0.0
        self.lat = 0.0
        self.lon = 0.0

        register_fmu3_var(self, "vcal_knts", causality="input")
        register_fmu3_var(self, "agl_ft", causality="input")
        register_fmu3_var(self, "roll_rad", causality="input")
        register_fmu3_var(self, "pitch_rad", causality="input")
        register_fmu3_var(self, "psi_rad", causality="input")
        register_fmu3_var(self, "lat", causality="input")
        register_fmu3_var(self, "lon", causality="input")

        self.is_airbourne = False

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # AeroSim FlightControlCommand structure to send to the dynamics FMU
        self.flight_control_command = dict_to_namespace(aerosim_types.FlightControlCommand().to_dict())
        self.flight_control_command.power_cmd = np.array([0.0])
        register_fmu3_var(self, "flight_control_command", causality="output")

    def enter_initialization_mode(self):

        # Load the JSON with the flight waypoints

        try:
            file_path = os.path.join(self.waypoints_dir, self.waypoints_file)
            with open(file_path, 'r', encoding='utf-8') as file:
                json_waypoints = json.load(file)
                json_waypoints.reverse()
                self.waypoints = json_waypoints
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
        except json.JSONDecodeError:
            print(f"Error: The file '{file_path}' contains invalid JSON.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}") 

        if self.waypoints is not None:
            if len(self.waypoints) > 0:
                self.current_waypoint = self.waypoints.pop()

    def hold_altitude(self, target_altitude, target_speed):
        
        # Control elevator and throttle to control altitude and speed

        # PID Controller Parameters
        Kp = 0.005  # Proportional gain
        Kp_throttle = 0.01  # Proportional gain

        current_altitude = self.agl_ft
        current_speed = self.vcal_knts

        # Compute altitude error
        altitude_error = target_altitude - current_altitude

        # Adjust elevator
        elevator_command = Kp * altitude_error
        elevator_command = max(-0.1, min(0.1, elevator_command))
        self.flight_control_command.pitch_cmd = - elevator_command

        # Adjust throttle based on airspeed
        speed_error = target_speed - current_speed
        throttle_command = 0.75 + Kp_throttle * speed_error  # Base throttle + correction
        throttle_command = max(0, min(1, throttle_command))  # Limit between 0 and 1
        self.flight_control_command.power_cmd = np.array([throttle_command])

    def calculate_bearing(self, lat, lon):

        # Calculate bearing and distance to waypoint

        lat1, lon1, lat2, lon2 = map(math.radians, [self.lat, self.lon, lat, lon])
        delta_lon = lon2 - lon1
        x = math.sin(delta_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
        initial_bearing = math.atan2(x, y)
        distance = haversine_distance_meters(self.lat, self.lon, lat, lon,)
        return math.degrees(initial_bearing) % 360 , distance


    def do_step(self, current_time: float, step_size: float) -> bool:

        print(f"Power: {self.flight_control_command.power_cmd[0]:.2f}, Vcal: {self.vcal_knts:.2f}, AGL: {self.agl_ft:.2f}, Roll: {self.roll_rad:.2f} ft")
        print("Airbourne: " + str(self.is_airbourne))

        self.flight_control_command.roll_cmd = - 5.0 * self.roll_rad

        if not self.is_airbourne:
            # The aircraft is on the runway, apply full throttle
            self.flight_control_command.power_cmd = np.array([1.0])
            # At a safe speed, let's rotate and lift the nose
            if self.vcal_knts > 65:
                self.flight_control_command.pitch_cmd = -0.3

            self.flight_control_command.roll_cmd = - 5.0 * self.roll_rad

            self.flight_control_command.flap_cmd = 1.0

        else:
            # Once airbourne, we retract the flaps and set a controller to
            # hold to aim for a height of 150 meters and a speed of 80 knots

            self.flight_control_command.flap_cmd = 0.0

            self.hold_altitude(self.target_altitude, self.target_speed)

            if self.current_waypoint is not None:
                
                # Let's calculate the target heading and distance to the waypoint from our current position
                target_heading, dist_to_waypoint = self.calculate_bearing(self.current_waypoint['lat'], self.current_waypoint['lon'])
                current_heading = math.degrees(self.psi_rad)

                # Now calculate the heading error
                heading_error = (target_heading - current_heading + 180) % 360 - 180

                print(f"Target heading: {target_heading:.2f} Current heading: {current_heading:.2f} distance to waypoint: {dist_to_waypoint:.2f}")

                if heading_error > 0:
                    # Turn right
                    correction = 0.3 * min(abs(heading_error), 20)/20 
                    self.flight_control_command.roll_cmd = - 5.0 * (self.roll_rad - correction)
                else:
                    # Turn left
                    correction = 0.3 * min(abs(heading_error), 20)/20 
                    self.flight_control_command.roll_cmd = - 5.0 * (self.roll_rad + correction)

                if dist_to_waypoint < 200:
                    if len(self.waypoints) > 0:
                        self.current_waypoint = self.waypoints.pop()
                    else:
                        self.current_waypoint = None

            else:
                # Keep the wings level
                self.flight_control_command.roll_cmd = - 5.0 * self.roll_rad

        if self.agl_ft > 50:
            self.is_airbourne = True

        return True
        










        