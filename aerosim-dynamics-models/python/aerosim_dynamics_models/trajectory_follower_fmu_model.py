from aerosim_core import register_fmu3_var, register_fmu3_param
from aerosim_core import generate_trajectory, generate_trajectory_linear, lla_to_ned
from aerosim_data import types as aerosim_types
from aerosim_data import dict_to_namespace

from typing import Optional
import json

import numpy as np
from pythonfmu3 import Fmi3Slave


# Note: The class name is used as the FMU file name
class trajectory_follower_fmu_model(Fmi3Slave):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.author = "AeroSim"
        self.description = "Implementation of a trajectory follower model"
        self.time = 0.0
        register_fmu3_var(self, "time", causality="independent")

        # Define Aerosim interface output variables
        self.vehicle_state = dict_to_namespace(aerosim_types.VehicleState().to_dict())
        register_fmu3_var(self, "vehicle_state", causality="output")
        self.trajectory_visualization = dict_to_namespace(
            aerosim_types.TrajectoryVisualization().to_dict()
        )
        register_fmu3_var(self, "trajectory_visualization", causality="output")

        self.waypoints_json_path = "trajectories/trajectory_follower_fmu_points.json"
        register_fmu3_param(self, "waypoints_json_path")
        self.use_linear_interpolation = False
        register_fmu3_param(self, "use_linear_interpolation")
        self.time_step_in_seconds = 0.01
        register_fmu3_param(self, "time_step_in_seconds")
        self.world_origin_latitude = 0.0
        register_fmu3_param(self, "world_origin_latitude")
        self.world_origin_longitude = 0.0
        register_fmu3_param(self, "world_origin_longitude")
        self.world_origin_altitude = 0.0
        register_fmu3_param(self, "world_origin_altitude")
        self.curvature_roll_factor = 1.0
        register_fmu3_param(self, "curvature_roll_factor")
        self.max_roll_rate_deg_per_second = 10.0
        register_fmu3_param(self, "max_roll_rate_deg_per_second")
        self.display_future_trajectory = False
        register_fmu3_param(self, "display_future_trajectory")
        self.display_past_trajectory = False
        register_fmu3_param(self, "display_past_trajectory")
        self.highlight_user_defined_waypoints = False
        register_fmu3_param(self, "highlight_user_defined_waypoints")
        self.number_of_future_waypoints = 1
        register_fmu3_param(self, "number_of_future_waypoints")
        self.actor_id = "actor1"
        register_fmu3_param(self, "actor_id")

        self.trajectory_start_timestamp_sec = 0
        self.generated_trajectory = []
        self.current_waypoint_index = 0
        self.last_index = 0
        self.future_trajectory_steps = 0
        self.user_defined_waypoints = np.array([])

        self.trajectory_visualization_settings = dict_to_namespace(
            aerosim_types.TrajectoryVisualizationSettings().to_dict()
        )
        self.trajectory_visualization_user_defined_waypoints = dict_to_namespace(
            aerosim_types.TrajectoryWaypoints().to_dict()
        )
        self.trajectory_visualization_future_trajectory = dict_to_namespace(
            aerosim_types.TrajectoryWaypoints().to_dict()
        )

    def enter_initialization_mode(self):
        with open(self.waypoints_json_path, "r", encoding="utf-8") as file:
            json_points = json.load(file)

        self._set_trajectory_visualization_settings()
        self._generate_user_defined_waypoints(json_points)
        self.trajectory_visualization.settings.display_future_trajectory = (
            self.trajectory_visualization_settings.display_future_trajectory
        )
        self.trajectory_visualization.settings.display_past_trajectory = (
            self.trajectory_visualization_settings.display_past_trajectory
        )
        self.trajectory_visualization.settings.highlight_user_defined_waypoints = (
            self.trajectory_visualization_settings.highlight_user_defined_waypoints
        )
        self.trajectory_visualization.settings.number_of_future_waypoints = (
            self.trajectory_visualization_settings.number_of_future_waypoints
        )
        self.trajectory_visualization.user_defined_waypoints.waypoints = (
            self.trajectory_visualization_user_defined_waypoints.waypoints,
        )

        self._generate_trajectory(json_points)
        self.trajectory_start_timestamp_sec = (
            self.generated_trajectory[0][0].sec
            + self.generated_trajectory[0][0].nanosec * 1.0e-9
        )

    def exit_initialization_mode(self):
        pass

    def do_step(self, current_time, step_size) -> bool:
        # Do time step calcs
        self.time = current_time + step_size

        latest_state = self._get_latest_state()
        if latest_state is None:
            raise ValueError("No valid vehicle state found")

        self._update_vehicle_state(latest_state)
        self._update_future_trajectory()
        return True

    def terminate(self):
        print("Terminating trajectory controller model.")
        self.time = 0.0

    def _generate_user_defined_waypoints(self, json_points: list) -> None:
        ned_points = []
        for point in json_points:
            ned = lla_to_ned(
                point["lat"],
                point["lon"],
                point["alt"],
                self.world_origin_latitude,
                self.world_origin_longitude,
                self.world_origin_altitude,
            )
            ned_points.append(ned)

        self.user_defined_waypoints = np.array(ned_points)
        self.trajectory_visualization_user_defined_waypoints.waypoints = json.dumps(
            self.user_defined_waypoints.tolist()
        )

    def _generate_trajectory(self, json_points: list) -> None:
        if self.use_linear_interpolation:
            points = [
                (point["time"], point["lat"], point["lon"], point["alt"])
                for point in json_points
            ]
            self.generated_trajectory = generate_trajectory_linear(
                points,
                self.time_step_in_seconds,
                (
                    self.world_origin_latitude,
                    self.world_origin_longitude,
                    self.world_origin_altitude,
                ),
            )
        else:
            points = []
            for point in json_points:
                time_val = point["time"]
                lat_val = point["lat"]
                lon_val = point["lon"]
                alt_val = point["alt"]
                roll_val = point.get("roll")
                pitch_val = point.get("pitch")
                yaw_val = point.get("yaw")
                ground_val = point.get("ground")
                points.append(
                    (
                        time_val,
                        lat_val,
                        lon_val,
                        alt_val,
                        roll_val,
                        pitch_val,
                        yaw_val,
                        ground_val,
                    )
                )

            self.generated_trajectory = generate_trajectory(
                points,
                self.time_step_in_seconds,
                self.max_roll_rate_deg_per_second,
                self.curvature_roll_factor,
                (
                    self.world_origin_latitude,
                    self.world_origin_longitude,
                    self.world_origin_altitude,
                ),
            )

    def _get_latest_state(self) -> Optional[aerosim_types.VehicleState]:
        # Update vehicle state to the latest interpolated trajectory
        latest_state = None
        for timestamp, vehicle_state in self.generated_trajectory:
            veh_state_timestamp_sec = (
                timestamp.sec + timestamp.nanosec * 1.0e-9
            ) - self.trajectory_start_timestamp_sec
            if veh_state_timestamp_sec <= self.time:
                latest_state = vehicle_state
            else:
                break
        return latest_state

    def _update_vehicle_state(self, latest_state: aerosim_types.VehicleState) -> None:
        # Copy each field inpenedently or else the reference is lost at the FMU output variable
        self.vehicle_state.state.pose.position.x = latest_state.state.pose.position.x
        self.vehicle_state.state.pose.position.y = latest_state.state.pose.position.y
        self.vehicle_state.state.pose.position.z = latest_state.state.pose.position.z
        self.vehicle_state.state.pose.orientation.x = (
            latest_state.state.pose.orientation.x
        )
        self.vehicle_state.state.pose.orientation.y = (
            latest_state.state.pose.orientation.y
        )
        self.vehicle_state.state.pose.orientation.z = (
            latest_state.state.pose.orientation.z
        )
        self.vehicle_state.state.pose.orientation.w = (
            latest_state.state.pose.orientation.w
        )
        self.vehicle_state.velocity.x = latest_state.velocity.x
        self.vehicle_state.velocity.y = latest_state.velocity.y
        self.vehicle_state.velocity.z = latest_state.velocity.z
        self.vehicle_state.angular_velocity.x = latest_state.angular_velocity.x
        self.vehicle_state.angular_velocity.y = latest_state.angular_velocity.y
        self.vehicle_state.angular_velocity.z = latest_state.angular_velocity.z
        self.vehicle_state.acceleration.x = latest_state.acceleration.x
        self.vehicle_state.acceleration.y = latest_state.acceleration.y
        self.vehicle_state.acceleration.z = latest_state.acceleration.z
        self.vehicle_state.angular_acceleration.x = latest_state.angular_acceleration.x
        self.vehicle_state.angular_acceleration.y = latest_state.angular_acceleration.y
        self.vehicle_state.angular_acceleration.z = latest_state.angular_acceleration.z

    def _set_trajectory_visualization_settings(self) -> None:
        self.trajectory_visualization_settings.display_future_trajectory = (
            self.display_future_trajectory
        )
        self.trajectory_visualization_settings.display_past_trajectory = (
            self.display_past_trajectory
        )
        self.trajectory_visualization_settings.highlight_user_defined_waypoints = (
            self.highlight_user_defined_waypoints
        )
        self.trajectory_visualization_settings.number_of_future_waypoints = (
            self.number_of_future_waypoints
        )

    def _get_future_trajectory(self) -> np.array:
        if self.current_waypoint_index + self.number_of_future_waypoints >= len(
            self.user_defined_waypoints
        ):
            return np.array([])
        tolerance = 1e-6
        goal = self.user_defined_waypoints[
            self.current_waypoint_index + self.number_of_future_waypoints
        ]
        future_trajectory = []
        trajectory = self.generated_trajectory[self.last_index :]
        skip = 20
        for i, (_, vehicle_state) in enumerate(trajectory):
            pos_x, pos_y, pos_z = (
                vehicle_state.state.pose.position.x,
                vehicle_state.state.pose.position.y,
                vehicle_state.state.pose.position.z,
            )
            if (
                abs(pos_x - goal[0]) < tolerance
                and abs(pos_y - goal[1]) < tolerance
                and abs(pos_z - goal[2]) < tolerance
            ):
                self.current_waypoint_index += self.number_of_future_waypoints
                self.last_index += i
                future_trajectory.append((pos_x, pos_y, pos_z))
                break
            if skip == 0:
                future_trajectory.append((pos_x, pos_y, pos_z))
                skip = 20
            else:
                skip -= 1
        return np.array(future_trajectory)

    def _update_future_trajectory(self) -> None:
        if self.display_future_trajectory:
            if self.future_trajectory_steps <= 0:
                waypoints = self._get_future_trajectory()
                self.future_trajectory_steps = len(waypoints) * 10
                self.trajectory_visualization.future_trajectory.waypoints = json.dumps(
                    waypoints.tolist()
                )
            else:
                self.future_trajectory_steps -= 1
                waypoints = np.array([])
                self.trajectory_visualization.future_trajectory.waypoints = json.dumps(
                    waypoints.tolist()
                )
