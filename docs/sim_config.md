# Simulation configuration file

The simulation configuration file or *sim config file* is a JSON file where the simulation configuration is defined. This file defines the configuration of the 3D environment, the actors (for example vehicles) that play a role in the simulation and also the controllers, such as FMUs. The simulation configuration also defines synchronization options and time-step options.

Within the sim config JSON are several key fields to define different aspects of the simulation:

* [`clock`](#clock)
* [`orchestrator`](#orchestrator)
* [`world`](#world)
    * `origin`
    * `weather`
    * `actors`
    * `sensors`
* [`fmu_models`](#fmu-models)

---

## Clock

The clock governs the time step of the simulation. When the orchestrator publishes a clock event, components subscribed to the clock will advance a simulation step if they are configured to do so.

Parameters:

* `step_size_ms`: the size of the clock time-step in milliseconds
* `pace_1x_scale`: if `true`, the orchestrator will pause the next time step until `step_size_ms` has passed after recieving all sync topics

Example:

```json
    "clock": {
        "step_size_ms": 20,
        "pace_1x_scale": true
    },
```

---

## Orchestrator

The orchestrator manages and synchronizes the main components of the simulation.

* `sync_topics`: the orhestrator will wait for all these topics to return data before publishing a new clock message

Example:

```json

    ...

    "orchestrator": {
        "sync_topics": [
            {
                "topic": "aerosim.actor1.vehicle_state",
                "interval_ms": 20
            }
        ]
    },

    ...

```

---

## World

The `world` field defines the configuration of the 3D environment and the actors within it.

* `origin`: a set of geospatial coordinates to define the local coordinate origin of the simulation
* `actors`: a list of actors within the simulation, such as vehicles

__Origin__

The origin field specifies the `latitude`, `longitude` and `altitude` where the coordinate origin of the simulation will be defined. If you are using Cesium, the simulator will download a map tile corresponding to the given geospatial coordinates.

Example:

```json

    ...

        "origin": {
            "latitude": 33.936519,
            "longitude": -118.412698,
            "altitude": 0.0
        },

    ...

```

__Weather__

The `weather` field of the `world` section defines the weather preset for the simulation. There are 3 options, `Cloudy`, `ClearSky` and `FoggyAndCloudy`:

⚠️ Note: The Omniverse renderer does not support different weather presets.

```json

        ...

        "weather": {
            "preset": "Cloudy"
        },

        ...

```

__Actors__

The actors field contains a list of actors to spawn in the simulation, each actor entry has several fields:

* `id`: the ID used to reference the actor
* `type`: actor type, for example `airplane` or `drone`
* `usd`: the relative location of the USD file containing the 3D model to use for the actor, relative to the root directory of the *aerosim-assets* repository
* `description`: description of the actor, for user reference
* `transform`: transform offset for the vehicle to transform, rotate or scale the 3D model from its default position
    * `translation`: X, Y, Z translation measured in meters
    * `rotation`: Roll, Pitch, Yaw angle measured in degrees, applied as an intrinsic rotation in roll, pitch, yaw order
    * `scale`: scale parameters in the X, Y, Z directions
* `state`: the topic used to publish the actor's state
* `effectors`: a list of effectors acting on the vehicle

Each effector has the same fields as listed above, but they are relevant specifically to the effector.

Example:

```json

    ...

    "actors": [
            {
                "id": "actor1",
                "type": "airplane",
                "usd": "vehicles/generic_aircraft",
                "description": "Generic aircraft model",
                "transform": {
                    "translation": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "state": {
                    "type": "dynamic",
                    "topic": "aerosim.actor1.vehicle_state"
                },
                "effectors": [
                    {
                        "id": "propeller_front",
                        "type": "airplane_propeller",
                        "usd": "generic_aircraft/propeller",
                        "transform": {
                            "translation": [3.1, 0.0, 0.0],
                            "rotation": [0.0, -90.0, 0.0],
                            "scale": [1.0, 1.0, 1.0]
                        },
                        "state": {
                            "type": "dynamic",
                            "topic": "aerosim.actor1.effector1.state"
                        }
                    }
                ]
            }
        ],

    ...

```

The USD path is given relative to the root directory of the aerosim-assets repository downloaded during installation. The given name should be the name of the directory containing the root USD model. In the case of effectors using a sub-component of a USD model, the USD path should be given relative to the root primitive object.

__Sensors__

The `sensors` section defines the configuration of sensors to be used in the simulation. The following shows the configuration for a single RGB camera:

```json

        ...

        "sensors": [
            {
                "sensor_name": "rgb_camera_0",
                "type": "sensors/cameras/rgb_camera",
                "parent": "actor1",
                "transform": {
                    "translation": [-20.0, 0.0, -5.0],
                    "rotation": [0.0, -10.0, 0.0 ]
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

        ...

```

---

## Renderers

The renderers section defines which renderers are active and which cameras will be assigned to each renderer. The following configuration shows a single renderer assigned to render a single camera with ID `rgb_camera_0`. The `viewport_config` defines a camera assigned to the renderer viewport, for simulation monitoring in the renderer's native interface or through Pixel Streaming to the AeroSim App.

```json

    ...

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

---

## FMU models

The `fmu_models` field contains a list of all FMUs used within the simulation. There can be multiple and they can be interconnected or connected with other parts of the simulation through data topics. Each FMU list entry contains several fields:

* `id`: an ID to reference the FMU instance
* `fmu_model_path`: path to the `.fmu` model file, relative to the directory where the client script is executed
* `component_type`: TO_BE_DELETED
* `component_input_topics`: a list of topics for the FMU driver to subscribe to to receive input data
* `component_output_topics`: a list of topics for the FMU driver to publish with FMU output data
* `fmu_aux_input_mapping`: an auxiliary mapping of message data to FMU input variables
* `fmu_aux_output_mapping`: an auxiliary mapping of FMU output variables to message data
* `fmu_init_vals`: initialization values to be sent to the FMU on initialization

The `fmu_aux_input_mapping` and `fmu_aux_output_mapping` fields can be used to map FMU input/output variables that do not conform to an existing AeroSim message type to specific parameters if needed.

Example:

```json

    ...


    "fmu_models": [
        {
            "id": "tutorial_fmu",
            "fmu_model_path": "fmu/tutorial_fmu.fmu",
            "component_type": "controller",
            "component_input_topics": [],
            "component_output_topics": [
                {
                    "msg_type": "vehicle_state",
                    "topic": "aerosim.actor1.vehicle_state"
                }
            ],
            "fmu_aux_input_mapping": {},
            "fmu_aux_output_mapping": {
                "aerosim.actor1.vehicle_state.pose": {
                    "position.x": "pos_x",
                    "position.y": "pos_y",
                    "position.z": "pos_z"
                }
            },
            "fmu_initial_vals": {
                "pos_x": 0.0,
                "pos_y": 0.0,
                "pos_z": 0.0
            }
        }
    ]

    ...

```

