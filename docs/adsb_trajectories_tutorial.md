# ADSB trajectories

This tutorial demonstrates how to process ADSB flight trajectory data for ingestion, simulation and visualization in AeroSim. In this tutorial you will learn:

* How to process ADSB data using AeroSim's Python utilities for ingestion
* How to simulate the flight and visualize the trajectory

Automatic Dependent Surveillance-Broadcast (ADSB) is a system that allows aircraft fo automatically broadcast their position and flight data in real time, for use in air traffic management, flight tracking and aviation research and safety. It is useful in simulation for modelling real-world scenarios in pilot training or performance research or for training and testing flight autonomy systems.

AeroSim provides tools to process ADSB data into data formats ready for the simulator to ingest, simulate and visualize the given flight trajectory. ADSB data can be derived from numerous sources on the web, such as the following:

* [ADS-B Exchange](https://www.adsbexchange.com/)
* [OpenSky Network](https://opensky-network.org/)
* [FAA SWIM](https://www.faa.gov/air_traffic/technology/swim)
* [FlightAware](https://www.flightaware.com/)


It's important to note that the ADSB data sources are not standardised, therefore there are differences in how the data is organized, which can be addressed with AeroSim's ADSB data formating tool that takes a common CSV format as input and allows specifying which column to use for the key data needed to extract the trajectories.

Example of ADSB data in CSV format:

```
timestamp,trackId,longitude,latitude,wgs84Altitude,mslAltitude,aglAltitude,speed,heading,hex_icao,nic,alt_baro,delta_time
1721956868.0,12345,-118.31887,33.82636,342.962284903872,379.095,356.1165142208855,0,298.58642578125,unknown,6,234.315,14.0
...
```

There are several pieces of information we are interested in for each trajectory point:

* Timestamp
* Latitude
* Longitude
* Altitude

We also need to identify the type of altitude we wish to use. Most ADSB data includes 3 different forms of altitude:

* __WGS84 - World Geodetic System 1984__: A global reference system used for GPS coordinates. The WGS84 altitude is measured relative to an ellipsoidal model of the Earth and is often used in navigation, GPS systems and flight management systems (FMS)
* __MSL - Mean Sea Level__: This measures the altitude with reference to the average height of the ocean's surface. This is normally the altitude reported by altimeters installed in standard aircraft.
* __AGL - Above Ground Level__: This is the altitude with reference to the height of the Earth's surface directly below the aircraft and would normally be measured by an aircraft's radioaltimeter.

In this case, we will chose to use the *WGS84* altitude.

## Converting the ADSB data

To convert the ADSB data into a compatible format, we will use the `generate_trajectory_from_adsb_csv` method from `aerosim_core`. Since the data can be organized differently depending upon the source of the ADSB data, we need to identify the relevant columns of the CSV data in the parameters, shown in the example snippet below.

```py
# Import AeroSim libraries and methods
from aerosim import AeroSim
from aerosim_core import generate_trajectory_from_adsb_csv

from pathlib import Path

# Identify the time type and timestamp column
time_type = "UNIX"
time_csv_column = 0

# Identify the chosen flight ID and
# the CSV column with the flight IDs
id = "12345"
id_csv_column = 1

# Position data
latitude_csv_column = 3 # Latitude column
longitude_csv_column = 2 # Longitude column

# Identify the altitude type we choose and
# the CSV column with the altitude data
altitude_type = "WGS84"
altitude_csv_column = 4

# Input CSV location
csv_filepath = "{path to your ADSB data}.csv"
csv_filepath = str(Path(csv_filepath).resolve())

# Output location for JSON data
out_dir = "trajectories"
out_dir = Path(out_dir).resolve()

# Generate the trajectory JSON
generate_trajectory_from_adsb_csv(csv_filepath, \
                                  str(out_dir), \
                                  time_csv_column, \
                                  latitude_csv_column, \
                                  longitude_csv_column, \
                                  altitude_csv_column, \
                                  altitude_type, \
                                  time_type, \
                                  id_csv_column, id)
```

An example JSON file output from the `generate_trajectory_from_adsb_csv()` function is provided in the `tutorials/trajectories` directory named `12345_generate_trajectory.json` as a trajectory extracted for track ID `12345` with the following format:

```json
[
  {
    "time": 0.0,
    "lat": 33.74625,
    "lon": -118.25619,
    "alt": 116.09004753400004
  },
  {
    "time": 8.0,
    "lat": 33.74381,
    "lon": -118.25803,
    "alt": 146.55726534027195
  },
  ...
]
```

In the JSON file is a list of items containing fields for time, latitude, longitude and altitude, which is ready for ingestion into an FMU.

## Simulating the generated trajectory

Now that we have the ADSB data processed into a format that can be ingested by the trajectory follower FMU, we need to configure the simulator to simulate the trajectory. We will use the trajectory follower FMU included in the `examples/fmu/` folder to process the JSON trajectory generated from the ADSB data into commands for the renderer.

Set up the Python launch script in a new file called `run_adsb_trajectory.py`:

```py
from aerosim import AeroSim

# --------------------------------------------
# Set path to configuration file

json_config_file = "config/sim_config_adsb_trajectory.json"

# --------------------------------------------
# Run AeroSim simulation

aerosim = AeroSim()
aerosim.run(json_config_file)

# --------------------------------------------
# Let the simulation run

try:
    input("Simulation is running. Press any key to stop...")
except KeyboardInterrupt:
    print("Simulation stopped.")
finally:
    # --------------------------------------------
    # Stop AeroSim simulation
    aerosim.stop()
```

Then set up the configuration file in a JSON file called `sim_config_adsb_trajectory.json`:

The principal fields `clock`, `orchestrator` and `world` are configured similar to previous tutorials.

```json
{
    "description": "Example of using a trajectory follower as an FMU.",
    "clock": {
        "step_size_ms": 20,
        "pace_1x_scale": true
    },
    "orchestrator": {
        "sync_topics": [
            {
                "topic": "aerosim.actor1.vehicle_state",
                "interval_ms": 20
            }
        ]
    },
    "world": {
        "update_interval_ms": 20,
        "origin": {
            "latitude": 33.74625,
            "longitude": -118.25619,
            "altitude": 116.09
        },
        "weather": {
            "preset": "Cloudy"
        },
        "actors": [
            {
                "actor_name": "actor1",
                "actor_asset": "vehicles/generic_airplane/generic_airplane",
                "parent": "",
                "description": "Generic aircraft model",
                "transform": {
                    "position": [
                        0.0,
                        0.0,
                        0.0
                    ],
                    "rotation": [
                        0.0,
                        0.0,
                        0.0
                    ],
                    "scale": [
                        1.0,
                        1.0,
                        1.0
                    ]
                },
                "state": {
                    "msg_type": "aerosim::types::VehicleState",
                    "topic": "aerosim.actor1.vehicle_state"
                },
                "effectors": [
                    {
                        "id": "propeller_front",
                        "relative_path": "generic_airplane/propeller",
                        "transform": {
                            "translation": [
                                0.0,
                                0.0,
                                0.0
                            ],
                            "rotation": [
                                0.0,
                                0.0,
                                0.0
                            ],
                            "scale": [
                                1.0,
                                1.0,
                                1.0
                            ]
                        },
                        "state": {
                            "msg_type": "aerosim::types::EffectorState",
                            "topic": "aerosim.actor1.propeller.effector_state"
                        }
                    }
                ],
                "trajectory_visualization": {
                    "msg_type": "aerosim::types::TrajectoryVisualization",
                    "topic": "aerosim.actor1.trajectory_visualization"
                }
            }
        ],
        "sensors": [
            {
                "sensor_name": "rgb_camera_0",
                "type": "sensors/cameras/rgb_camera",
                "parent": "actor1",
                "transform": {
                    "translation": [
                        -20.0,
                        0.0,
                        -5.0
                    ],
                    "rotation": [
                        0.0,
                        -10.0,
                        0.0
                    ]
                },
                "parameters": {
                    "resolution": [
                        1920,
                        1080
                    ],
                    "tick_rate": 0.02,
                    "frame_rate": 30,
                    "fov": 90,
                    "near_clip": 0.1,
                    "far_clip": 1000.0,
                    "capture_enabled": false
                }
            }
        ]
    },
    "renderers": [
        {
            "renderer_id": "0",
            "role": "primary",
            "sensors": [
                "rgb_camera_0"
            ],
            "viewport_config": {
                "active_camera": "rgb_camera_0"
            }
        }
    ],

    ...

```

In the FMU section, we will nominate the `trajectory_follower_fmu_model.fmu` unit found in the `examples/fmu` folder to process the converted ADSB trajectory data into a sequence of poses to send to the renderer.

```json

    ...

    "fmu_models": [
        {
            "id": "trajectory_follower",
            "fmu_model_path": "examples/fmu/trajectory_follower_fmu_model.fmu",
            "component_input_topics": [],
            "component_output_topics": [
                {
                    "msg_type": "aerosim::types::VehicleState",
                    "topic": "aerosim.actor1.vehicle_state"
                }
            ],
            "fmu_aux_input_mapping": {},
            "fmu_aux_output_mapping": {},
            "fmu_initial_vals": {
                "waypoints_json_path": "trajectories/12345_generated_trajectory.json",
                "display_future_trajectory": true,
                "display_past_trajectory": true,
                "highlight_user_defined_waypoints": true,
                "number_of_future_waypoints": 1,
                "use_linear_interpolation": false,
                "time_step_in_seconds": 0.01,
                "curvature_roll_factor": 1.0,
                "max_roll_rate_deg_per_second": 10.0
            }
        }
    ]
}
```

In the `fmu_initial_vals` section, we need to provide the directory and filename of the trajectory JSON generated earlier via the `waypoints_json_path` field. The `use_linear_interpolation` parameter can be set to true if linear interpolation of the trajectory between waypoints is desired instead of curved spline interpolation.

## Run the simulation

After configuring the JSON file, make sure to activate the AeroSim virtual environment and then run the script:

```sh
source .venv/bin/activate
cd tutorials/
# Windows .\.venv\Scripts\activate
# Windows cd .\tutorials\

python run_adsb_trajectory.py
```
