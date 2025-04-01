# Scene graph reference

The scene graph is a data structure used by AeroSim to contain a logical representation of the 3D scene to be visualized in the renderer. It uses the Entity-Component-System (ECS) to represent the relationship between objects in the scene. It can be thought of as a collections of nodes in a graph representing relationships between entities. For example an aircraft's airframe model can be related to child objects representing the moving parts of the aircraft like rotors or propellers. 

The scene graph representation comprises entities and components. Entities represent general purpose objects, for example, a vehicle or an aircraft. Componenents characterize some aspect of an entity. For example, an aicraft model has a 3D model representing the fuselage, it may also have several rotors, therefore these become components associated with the entity representing the aircraft. The aircraft's state (e.g. pose and position) is also an aspect of the aircraft entity that is represented as a component.

In AeroSim, the scene graph is represented through a JSON schema, which is communicated to the renderer through a data topic. 

## Scene graph schema

The scene graph schema has 3 principal fields:

* `entities`: a list of the entities in the simulation, e.g. vehicles
* `resources`: properties associated with the whole scene, e.g. the world origin
* `components`: a list of the components associated with the entities listed in the `entities` field

### Entities

The entities list contains the list of entities in the simulation. Each entry should be labelled with the entity ID, e.g. `entity_0`, and should contain a list of the component groups which contain components relating to the entity. In the following example, you can see that `entity_0` has associated components in the `actor_properties`, `actor_state` and `effectors` component group, while `entity_2` has no associated components in the `effectors` group, but has associated components in the `sensors` group.

```json
{
    "entities": {
        "entity_0": [
            "actor_properties", "actor_state", "effectors"
        ],
        "entity_1": [
            "actor_properties", "actor_state", "effectors"
        ],
        "entity_2": [
            "actor_properties", "actor_state", "sensor"
        ],
        "entity_3": [
            "actor_properties", "actor_state", "sensor"
        ]
    },

    ...

}
```

### Components

The components list contains several component groups:

* `actor_properties`: any properties associated with an actor entity, for example, parents, 3D assets or names/IDs
* `actor_state`: any properties associated with an actor's state, such as position and pose 
* `effectors`: any effectors related to an actor entity, such as rotors
* `sensors`: any sensors related to an actor entity, such as cameras or IMUs

#### Actor properties

The actor properties group should contain a list of general properties associated with an actor entity. This includes the following fields:

`actor_name`: a name chosen to identify the actor 
`actor_asset`: the location of a 3D assets associated with the actor (e.g. an aircraft fuselage model)
`parent`: an entity ID that identifies a parent for the given entity

In the following example, you can see that `entity_2` is a camera sensor, and is parented to `entity_1` which means that it's location in the simulation will be governed by its parent entity.


```json
{


    "components": {
        "actor_properties": {
            "entity_0": {
                "actor_name": "generic_evtol_0",
                "actor_asset": "generic-aircrafts/GenericEVtol/GenericEVTOL",
                "parent": ""
            },
            "entity_1": {
                "actor_name": "generic_evtol_1",
                "actor_asset": "generic-aircrafts/GenericEVtol/GenericEVTOL",
                "parent": ""
            },
            "entity_2": {
                "actor_name": "rgb_camera_0",
                "actor_asset": "Sensors/Cameras/RGBCamera",
                "parent": "entity_1"
            },

            ...

        }
    }
```

#### Actor state components

The `actor_state` component group contains information relating to the state of each entity, including the transform (position, orientation and scale), along with positions translated into different coordinate systems.

* `pose`: the pose of the actor in simulation coordinates
    * `transform`
        * `position` - in simulation coordinates in meters
            * `x`, `y`, `z`
        * `orientation` - in quaternion format
            * `x`, `y`, `z`, `w`
        * `scale` - scale parameter for each dimension
            * `x`, `y`, `z`
    * `world_coordinate` - world coordinates in different coordinate conventions
        * `ned` - in North, East, Down format
        * `lla` - in Latitude, Longitude, Altitude format
        * `ecef` - in Earth Centered, Earth Fixed coordinates
        * `cartesian` - 
        * `origin_lla` - 
        * `ellipsoid` - 

The following example demonstrates the form of an `actor_state` component.

```json

        ...

        "actor_state": {
            "entity_0": {
                "pose": {
                    "transform": {
                        "position": {"x": 0.0,"y": 0.0,"z": 0.0},
                        "orientation": {"x": 0.0,"y": 0.0,"z": 0.0,"w": 1.0 },
                        "scale": {"x": 1.0,"y": 1.0,"z": 1.0}
                    }
                },
                "world_coordinate": {
                    "ned": {
                        "north": 0.0,
                        "east": 0.0,
                        "down": 0.0
                    },
                    "lla": {
                        "latitude": 29.594656,
                        "longitude": -95.16384722,
                        "altitude": -28.3
                    },
                    "ecef": {
                        "x": 0.0,"y": 0.0,"z": 0.0
                    },
                    "cartesian": {
                        "x": 0.0,"y": 0.0,"z": 0.0
                    },
                    "origin_lla": {
                        "latitude": 29.594656,
                        "longitude": -95.16384722,
                        "altitude": -28.3
                    },
                    "ellipsoid": {
                        "equatorial_radius": 6378137.0,
                        "flattening_factor": 0.0033528106647474805,
                        "polar_radius": 6356752.314245179
                    }
                }
            },

            ...

```

#### Effector components

The effectors component group contains information about any effectors to be associated with an entity, for example rotors, propellers or jet engines.

For each effector, the following fields are necessary:

* `id`: the effector ID
* `usd_relative_path`: the relative path location of the USD 3D asset for the effector
* `pose`: the pose in simulation coordinates
    * `transform` 
        * `position` - __relative__ position in simulation space to parent entity
            * `x`, `y`, `z` 
        * `orientation` - __relative__ orientation in simulation space to parent entity, in quaternion format
            * `x`, `y`, `z`, `w`
        * `scale` - scale parameter for each dimension
            * `x`, `y`, `z`

The following example demonstrates an entry for a rotor blade component associated with `entity_0`:

```json

        ...

        "effectors": {
            "entity_0": [
                {
                    "id": "rotor_blade_01",
                    "usd_relative_path": "evtol/VTOLGeneric_Armature/rotor_blade_01",
                    "pose": {
                        "transform" : {
                            "position": {"x": 3.0643,"y": 3.147,"z": 1.8735},
                            "orientation": {"x": 0.0,"y": 0.0,"z": 0.0,"w": 1.0},
                            "scale": {"x": 1.0,"y": 1.0,"z": 1.0}
                        }
                    }
                },

        ...

```

#### Sensor components

The sensor components group contains information about sensors associated with entities from the entities list. For each entity associated with a sensor, an entry should be made to this list with the following fields:

* `sensor_name`: a name chosen to identify the sensor
* `sensor_type`: a sensor type specification
* `sensor_parameters`: a set of fields with parameters relevant to the sensor. The parameters contained in this object will differ depening on the chosen sensor type

The following example demonstrates a sensor component configuration for an RGB camera sensor. 


```json

        ...

        "sensor": {
            "entity_2": {
                "sensor_name": "rgb_camera_0",
                "sensor_type": "rgb_camera",
                "sensor_parameters": {
                    "resolution": {
                        "x": 1920,
                        "y": 1080
                    },
                    "tick_rate": 0.2,
                    "fov": 90,
                    "near_clip": 0.1,
                    "far_clip": 1000.0
                }
            },

        ...

```