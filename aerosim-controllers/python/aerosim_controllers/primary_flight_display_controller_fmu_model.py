from aerosim_core import (
    register_fmu3_var,
    register_fmu3_param,
    bearing_deg,
    deviation_from_course_meters,
)
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

from pythonfmu3 import Fmi3Slave
import math

# Deviation scale factor as 5 nautical miles = 12 degrees and 1852 m / naut mile
COURSE_DEVIATION_METERS_TO_DEG = 1.0 / 1852.0 / 5.0 * 12.0


# Note: The class name is used as the FMU file name
class primary_flight_display_controller_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Autopilot waypoint tracking variables
        self.cur_target_wp_lat_deg = 0.0
        self.cur_target_wp_long_deg = 0.0
        self.prev_target_wp_lat_deg = 0.0
        self.prev_target_wp_long_deg = 0.0

        # ---------------------------------------------------------------------

        # FMU general variables
        self.author = "AeroSim"
        self.description = "Implementation of a Primary Flight Display controller model"

        # FMU 3.0 requires a time variable set with independent causality
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # ---------------------------------------------------------------------

        # Define Aerosim interface output variables
        self.primary_flight_display_data = dict_to_namespace(
            aerosim_types.PrimaryFlightDisplayData().to_dict()
        )
        register_fmu3_var(self, "primary_flight_display_data", causality="output")

        # ---------------------------------------------------------------------

        # Define auxiliary input variables

        ## Inputs from flight dynamics model

        self.velocities_vc_kts = 0.0
        register_fmu3_var(self, "velocities_vc_kts", causality="input")

        self.velocities_vtrue_kts = 0.0
        register_fmu3_var(self, "velocities_vtrue_kts", causality="input")

        self.position_h_sl_ft = 0.0
        register_fmu3_var(self, "position_h_sl_ft", causality="input")

        self.velocities_h_dot_fps = 0.0
        register_fmu3_var(self, "velocities_h_dot_fps", causality="input")

        self.attitude_pitch_rad = 0.0
        register_fmu3_var(self, "attitude_pitch_rad", causality="input")

        self.attitude_roll_rad = 0.0
        register_fmu3_var(self, "attitude_roll_rad", causality="input")

        self.accelerations_vdot_ft_sec2 = 0.0
        register_fmu3_var(self, "accelerations_vdot_ft_sec2", causality="input")

        self.attitude_heading_true_rad = 0.0
        register_fmu3_var(self, "attitude_heading_true_rad", causality="input")

        self.position_lat_geod_rad = 0.0
        register_fmu3_var(self, "position_lat_geod_rad", causality="input")

        self.position_long_gc_rad = 0.0
        register_fmu3_var(self, "position_long_gc_rad", causality="input")

        ## Inputs from autopilot

        self.target_altitude_ft = 0.0
        register_fmu3_var(self, "target_altitude_ft", causality="input")

        self.target_wp_active = False
        register_fmu3_var(self, "target_wp_active", causality="input")

        self.target_wp_latitude_deg = 0.0
        register_fmu3_var(self, "target_wp_latitude_deg", causality="input")

        self.target_wp_longitude_deg = 0.0
        register_fmu3_var(self, "target_wp_longitude_deg", causality="input")

        # ---------------------------------------------------------------------

        # Define parameters

        self.altimeter_pressure_setting_inhg = 29.92
        register_fmu3_param(self, "altimeter_pressure_setting_inhg")

        self.hsi_mode = "gps"
        register_fmu3_param(self, "hsi_mode")

        # ---------------------------------------------------------------------

    def enter_initialization_mode(self):
        pass

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time, step_size) -> bool:
        # Do time step calcs
        self.time = current_time

        # Currently, altimeter pressure setting is set by initial parameter instead
        # of user input
        self.primary_flight_display_data.altimeter_pressure_setting_inhg = (
            self.altimeter_pressure_setting_inhg
        )

        # Currently, HSI mode is set by initial parameter instead of user input
        if self.hsi_mode == "gps":
            self.primary_flight_display_data.hsi_mode = 0
        elif self.hsi_mode == "vor1":
            self.primary_flight_display_data.hsi_mode = 1
        elif self.hsi_mode == "vor2":
            self.primary_flight_display_data.hsi_mode = 2
        else:
            print("WARNING: Invalid HSI mode. Setting to default GPS mode.")
            self.primary_flight_display_data.hsi_mode = 0

        # Pass-through values
        self.primary_flight_display_data.airspeed_kts = self.velocities_vc_kts
        self.primary_flight_display_data.true_airspeed_kts = self.velocities_vtrue_kts
        self.primary_flight_display_data.target_altitude_ft = self.target_altitude_ft
        self.primary_flight_display_data.vertical_speed_fpm = (
            self.velocities_h_dot_fps * 60.0
        )  # ft/sec -> ft/min
        self.primary_flight_display_data.pitch_deg = math.degrees(
            self.attitude_pitch_rad
        )
        self.primary_flight_display_data.roll_deg = math.degrees(self.attitude_roll_rad)
        self.primary_flight_display_data.side_slip_fps2 = (
            self.accelerations_vdot_ft_sec2
        )
        self.primary_flight_display_data.heading_deg = math.degrees(
            self.attitude_heading_true_rad
        )

        # Adjust altimeter altitude by pressure setting
        self.primary_flight_display_data.altitude_ft = self.adjust_altitude_by_pressure(
            self.position_h_sl_ft
        )

        # Use autopilot waypoints for HSI course and deviation calculations (always
        # using GPS mode logic for now)
        if self.target_wp_active:
            # Update tracked waypoints if target waypoint changed
            eps = 1e-9
            did_target_wp_change = (
                abs(self.target_wp_latitude_deg - self.cur_target_wp_lat_deg) > eps
                or abs(self.target_wp_longitude_deg - self.cur_target_wp_long_deg) > eps
            )

            if did_target_wp_change:
                self.prev_target_wp_lat_deg = self.cur_target_wp_lat_deg
                self.prev_target_wp_long_deg = self.cur_target_wp_long_deg
                self.cur_target_wp_lat_deg = self.target_wp_latitude_deg
                self.cur_target_wp_long_deg = self.target_wp_longitude_deg

            # Calculate course and deviation
            course_deg = bearing_deg(
                self.prev_target_wp_lat_deg,
                self.prev_target_wp_long_deg,
                self.cur_target_wp_lat_deg,
                self.cur_target_wp_long_deg,
            )
            self.primary_flight_display_data.hsi_course_select_heading_deg = course_deg

            course_deviation_m = deviation_from_course_meters(
                self.prev_target_wp_lat_deg,
                self.prev_target_wp_long_deg,
                self.cur_target_wp_lat_deg,
                self.cur_target_wp_long_deg,
                math.degrees(self.position_lat_geod_rad),
                math.degrees(self.position_long_gc_rad),
            )
            # Convert deviation distance to angle using scale factor
            course_deviation_deg = course_deviation_m * COURSE_DEVIATION_METERS_TO_DEG
            self.primary_flight_display_data.hsi_course_deviation_deg = (
                course_deviation_deg
            )
        else:
            # No active target waypoint, so set waypoints to current position
            self.cur_target_wp_lat_deg = math.degrees(self.position_lat_geod_rad)
            self.cur_target_wp_long_deg = math.degrees(self.position_long_gc_rad)
            self.prev_target_wp_lat_deg = self.cur_target_wp_lat_deg
            self.prev_target_wp_long_deg = self.cur_target_wp_long_deg

            self.primary_flight_display_data.hsi_course_select_heading_deg = 0.0
            self.primary_flight_display_data.hsi_course_deviation_deg = 0.0

        return True

    def terminate(self):
        print("Terminating PFD controller model.")
        self.time = 0.0

    def adjust_altitude_by_pressure(self, altitude_ft):
        # Scale altitude by 1000 ft per inHG from 29.92 inHG standard atmos. pressure
        delta_inhg = 29.92 - self.altimeter_pressure_setting_inhg
        return altitude_ft + delta_inhg * 1000.0
