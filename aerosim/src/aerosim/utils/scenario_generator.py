import os
import json

def generate_scenario_json(trajectories_folder: str = "trajectories",
                           output_file: str = "auto_gen_scenario.json",
                           fmu_model_path: str = "dev_scripts/fmu/trajectory_follower_fmu_model.fmu",
                           sensor_configs: list = None,
                           add_sensors_to_vehicles: list = None,
                           weather_preset: str = "Cloudy",
                           renderer_viewport_config: dict = {"active_camera": "rgb_camera_0"}) -> None:
    """
    Generate a simulation scenario JSON using the new scenario schema.
    
    The generated scenario includes:
      - A clock with fixed step size.
      - An orchestrator with sync topics.
      - A world with an origin based on the first waypoint, updated weather, actors with trajectory visualization,
        and sensors attached as specified.
      - A primary renderer using the provided sensor configuration.
      - FMU models for trajectory following per actor and additional sensor FMU models for the first actor.
    
    Args:
        trajectories_folder (str): Directory containing trajectory JSON files.
        output_file (str): Output file path for the generated scenario JSON.
        fmu_model_path (str): Path to the trajectory follower FMU model file.
        sensor_configs (list): List of sensor configurations to attach (default provided if None).
        add_sensors_to_vehicles (list): List of vehicle names to which sensors should be attached.
            If None or empty, sensors are attached to the first actor encountered.
        weather_preset (str): Weather preset for the simulation world.
        renderer_viewport_config (dict): Configuration for the primary renderer's viewport.
    """
    if sensor_configs is None:
        sensor_configs = [
            {
                "sensor_name": "rgb_camera_0",
                "type": "sensors/cameras/rgb_camera",  # updated to match sample scenario
                "transform": {
                    "translation": [-15.0, 0.0, -2.0],
                    "rotation": [0.0, -10.0, 0.0]
                },
                "parameters": {
                    "resolution": [1920, 1080],
                    "tick_rate": 0.02,
                    "frame_rate": 30,
                    "fov": 90,
                    "near_clip": 0.1,
                    "far_clip": 1000.0,
                    "capture_enabled": False
                }
            }
        ]
    if add_sensors_to_vehicles is None:
        add_sensors_to_vehicles = []

    # Base scenario structure
    scenario = {
        "description": "Multi-intruder scenario generated from trajectories.",
        "clock": {
            "step_size_ms": 20,
            "pace_1x_scale": True
        },
        "orchestrator": {
            "sync_topics": []  # updated schema: no create_topics
        },
        "world": {
            "update_interval_ms": 20,
            "origin": {},
            "weather": {
                "preset": weather_preset
            },
            "actors": [],
            "sensors": []
        },
        "renderers": [{
            "renderer_id": "0",
            "role": "primary",
            "sensors": [sensor['sensor_name'] for sensor in sensor_configs],
            "viewport_config": renderer_viewport_config
        }],
        "fmu_models": []
    }

    # Retrieve and sort trajectory files for consistent ordering
    trajectory_files = [f for f in os.listdir(trajectories_folder) if f.endswith('_trajectory.json')]
    trajectory_files.sort()

    for idx, traj_file in enumerate(trajectory_files, start=1):
        track_id = traj_file.split('_')[0]
        traj_path = os.path.join(trajectories_folder, traj_file)
        with open(traj_path, 'r') as file:
            waypoints = json.load(file)
        if not waypoints:
            continue
        first_waypoint = waypoints[0]
        if idx == 1:
            # Use the first waypoint to define the world origin (altitude defaults to reference value if not provided)
            scenario['world']['origin'] = {
                "latitude": first_waypoint['lat'],
                "longitude": first_waypoint['lon'],
                "altitude": first_waypoint.get('alt', 116.09)
            }
        actor_name = f"actor{track_id}"
        vehicle_topic = f"aerosim.{actor_name}.vehicle_state"
        trajectory_vis_topic = f"aerosim.{actor_name}.trajectory_visualization"
        effector_topic = f"aerosim.{actor_name}.effector1.state"

        # Add sync topic for the actor
        scenario['orchestrator']['sync_topics'].append({
            "topic": vehicle_topic,
            "interval_ms": 20
        })

        # Create actor configuration with updated asset path, effector state, and added trajectory visualization
        actor = {
            "actor_name": actor_name,
            "actor_asset": "vehicles/generic_airplane/generic_airplane",
            "parent": "",
            "description": f"Trajectory follower {track_id}",
            "transform": {
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0]
            },
            "state": {
                "msg_type": "aerosim::types::VehicleState",
                "topic": vehicle_topic
            },
            "effectors": [{
                "id": "propeller_front",
                "relative_path": "generic_airplane/propeller",
                "transform": {
                    "translation": [3.1, 0.0, 0.0],
                    "rotation": [0.0, -90.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "state": {
                    "msg_type": "aerosim::types::EffectorState",
                    "topic": effector_topic
                }
            }],
            "trajectory_visualization": {
                "msg_type": "aerosim::types::TrajectoryVisualization",
                "topic": trajectory_vis_topic
            }
        }
        scenario['world']['actors'].append(actor)

        # Attach sensors to vehicles if specified (default to first actor)
        if idx == 1 and not add_sensors_to_vehicles:
            add_sensors_to_vehicles.append(actor_name)

        if actor_name in add_sensors_to_vehicles:
            for sensor in sensor_configs:
                sensor_config = sensor.copy()
                sensor_config['parent'] = actor_name
                scenario['world']['sensors'].append(sensor_config)

        # Add trajectory follower FMU model for the actor using the updated initial values
        traj_follower_fmu = {
            "id": f"trajectory_follower_{track_id}",
            "fmu_model_path": fmu_model_path,
            "component_input_topics": [],
            "component_output_topics": [
                {
                    "msg_type": "aerosim::types::VehicleState",
                    "topic": vehicle_topic
                },
                {
                    "msg_type": "aerosim::types::TrajectoryVisualization",
                    "topic": trajectory_vis_topic
                }
            ],
            "fmu_aux_input_mapping": {},
            "fmu_aux_output_mapping": {},
            "fmu_initial_vals": {
                "waypoints_json_path": os.path.join(trajectories_folder, traj_file),
                "display_future_trajectory": True,
                "display_past_trajectory": True,
                "highlight_user_defined_waypoints": True,
                "number_of_future_waypoints": 1,
                "use_linear_interpolation": False,
                "time_step_in_seconds": 0.01,
                "curvature_roll_factor": 1.0,
                "max_roll_rate_deg_per_second": 10.0
            }
        }
        scenario['fmu_models'].append(traj_follower_fmu)

        # For the first actor, also add sensor FMU models (GNSS, ADSB, IMU)
        if idx == 1:
            # GNSS publisher
            gnss_fmu = {
                "id": "gnss_publisher",
                "fmu_model_path": "fmu/gnss_sensor_fmu_model.fmu",
                "component_type": "sensor",
                "component_input_topics": [
                    {
                        "msg_type": "aerosim::types::VehicleState",
                        "topic": vehicle_topic
                    }
                ],
                "component_output_topics": [],
                "fmu_aux_input_mapping": {},
                "fmu_aux_output_mapping": {},
                "fmu_initial_vals": {
                    "output_gnss_topic_name": f"aerosim.{actor_name}.sensor.gnss"
                }
            }
            scenario['fmu_models'].append(gnss_fmu)
            # ADSB publisher
            adsb_fmu = {
                "id": "adsb_publisher",
                "fmu_model_path": "fmu/adsb_sensor_fmu_model.fmu",
                "component_type": "sensor",
                "component_input_topics": [
                    {
                        "msg_type": "aerosim::types::VehicleState",
                        "topic": vehicle_topic
                    }
                ],
                "component_output_topics": [],
                "fmu_aux_input_mapping": {},
                "fmu_aux_output_mapping": {},
                "fmu_initial_vals": {
                    "output_adsb_topic_name": f"aerosim.{actor_name}.sensor.adsb"
                }
            }
            scenario['fmu_models'].append(adsb_fmu)
            # IMU publisher
            imu_fmu = {
                "id": "imu_publisher",
                "fmu_model_path": "fmu/imu_sensor_fmu_model.fmu",
                "component_type": "sensor",
                "component_input_topics": [
                    {
                        "msg_type": "aerosim::types::VehicleState",
                        "topic": vehicle_topic
                    }
                ],
                "component_output_topics": [],
                "fmu_aux_input_mapping": {},
                "fmu_aux_output_mapping": {},
                "fmu_initial_vals": {
                    "output_imu_topic_name": f"aerosim.{actor_name}.sensor.imu"
                }
            }
            scenario['fmu_models'].append(imu_fmu)

    with open(output_file, 'w') as outfile:
        json.dump(scenario, outfile, indent=4)
    print(f"Scenario JSON created at {output_file}")
