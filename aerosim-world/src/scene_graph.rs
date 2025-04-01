use ::log::{debug, info, warn};
use aerosim_data::types::trajectory::TrajectoryVisualizationSettings;
use aerosim_data::types::PrimaryFlightDisplayData;
use aerosim_data::types::TrajectoryVisualization;
use std::{collections::HashMap, time::Duration};

use serde_json::json;
use serde_json::Value;

use bevy_app::prelude::*;
use bevy_ecs::prelude::*;
use bevy_hierarchy::prelude::*;
use bevy_transform::{
    components::GlobalTransform,
    systems::{propagate_transforms, sync_simple_transforms},
};

use aerosim_core::coordinate_system::{geo::Ellipsoid, world_coordinate::WorldCoordinate};
use aerosim_data::{
    middleware::{AerosimDeserializeEnum, Serializer, SerializerEnum},
    types::{
        ActorState, AerosimMessage, EffectorState, JsonData, Pose, Quaternion, TimeStamp, Vector3,
        VehicleState,
    },
};

use crate::components::actor::*;
use crate::components::sensor::*;
use crate::components::trajectory::*;
use crate::components::world::*;

#[allow(unused)]
#[derive(AerosimDeserializeEnum, Debug)]
pub enum SceneGraphStateData {
    VehicleState(VehicleState),
    EffectorState(EffectorState),
    PrimaryFlightDisplayData(PrimaryFlightDisplayData),
    JsonData(JsonData),
    TrajectoryVisualization(TrajectoryVisualization),
}

pub struct SceneGraph {
    ecs_app: bevy_app::App,
    update_interval: Duration,
    last_update_time: Duration,
    entity_map: HashMap<String, Entity>,
    // entity_state_topic_map is a map of "topic" -> "entity_name"
    entity_state_topic_map: HashMap<String, String>,
    // entity_effector_state_topic_map is a map of "topic" -> ("entity_name", effector_idx)
    entity_effector_state_topic_map: HashMap<String, (String, usize)>,
    origin_lla: (f64, f64, f64),
    rotate_bevy_to_ned: bevy_math::Quat,
    rotate_ned_to_bevy: bevy_math::Quat,
}

impl SceneGraph {
    pub fn new() -> Self {
        let mut app = App::new();
        app.add_systems(Update, (sync_simple_transforms, propagate_transforms));
        app.add_systems(PostUpdate, SceneGraph::update_sim_coordinates);

        SceneGraph {
            ecs_app: app,
            update_interval: Duration::ZERO,
            last_update_time: Duration::ZERO,
            entity_map: HashMap::new(),
            entity_state_topic_map: HashMap::new(),
            entity_effector_state_topic_map: HashMap::new(),
            origin_lla: (0.0, 0.0, 0.0),
            rotate_bevy_to_ned: bevy_math::Quat::from_rotation_y(-std::f32::consts::PI / 2.0)
                * bevy_math::Quat::from_rotation_z(std::f32::consts::PI / 2.0),
            rotate_ned_to_bevy: bevy_math::Quat::from_rotation_z(-std::f32::consts::PI / 2.0)
                * bevy_math::Quat::from_rotation_y(std::f32::consts::PI / 2.0),
        }
    }

    fn bevy_xyz_to_ned(&self, bevy_point: bevy_math::Vec3) -> bevy_math::Vec3 {
        let xform = bevy_transform::components::Transform::from_rotation(self.rotate_bevy_to_ned);
        xform.transform_point(bevy_point)
    }

    fn ned_to_bevy_xyz(&self, ned_point: bevy_math::Vec3) -> bevy_math::Vec3 {
        let xform = bevy_transform::components::Transform::from_rotation(self.rotate_ned_to_bevy);
        xform.transform_point(ned_point)
    }

    fn ned_rpy_to_bevy_quat(&self, rpy: (f32, f32, f32)) -> bevy_math::Quat {
        let bevy_q = bevy_math::Quat::from_euler(
            bevy_math::EulerRot::YXZ,
            -rpy.2.to_radians(), // yaw
            rpy.1.to_radians(),  // pitch
            -rpy.0.to_radians(), // roll
        ); // Bevy default EulerRot is `YXZ` as yaw (y-axis), pitch (x-axis), roll (z-axis).
        bevy_q
    }

    fn bevy_quat_to_ned_quat(&self, bevy_quat: bevy_math::Quat) -> bevy_math::Quat {
        let (yaw, pitch, roll) = bevy_quat.to_euler(bevy_math::EulerRot::default());
        let ned_q = bevy_math::Quat::from_euler(bevy_math::EulerRot::ZYXEx, -roll, pitch, -yaw);
        ned_q
    }

    fn ned_quat_to_bevy_quat(&self, ned_quat: bevy_math::Quat) -> bevy_math::Quat {
        let (roll, pitch, yaw) = ned_quat.to_euler(bevy_math::EulerRot::ZYXEx);
        let bevy_q = bevy_math::Quat::from_euler(bevy_math::EulerRot::YXZ, -yaw, pitch, -roll);
        bevy_q
    }

    pub fn load_world(
        &mut self,
        world_config: &serde_json::Value,
        renderers_config: &serde_json::Value,
    ) {
        info!("Load the world scene graph from sim config.");

        if let Some(update_interval_ms) = world_config["update_interval_ms"].as_u64() {
            self.update_interval = Duration::from_millis(update_interval_ms)
        }

        // Add the world origin resource
        let world_origin_json = world_config["origin"]
            .as_object()
            .expect("Missing 'origin' field in 'world' config");
        let world_origin_resource = WorldOrigin {
            latitude: world_origin_json["latitude"].as_f64().unwrap(),
            longitude: world_origin_json["longitude"].as_f64().unwrap(),
            altitude: world_origin_json["altitude"].as_f64().unwrap(),
        };

        self.add_resource(world_origin_resource);

        // Add weather preset resource
        let weather_json = world_config
            .get("weather")
            .and_then(Value::as_object)
            .unwrap();
        let weather_preset = weather_json
            .get("preset")
            .and_then(Value::as_str)
            .unwrap_or("Cloudy")
            .to_string();
        let weather_resource = Weather {
            preset: weather_preset,
        };

        self.add_resource(weather_resource);

        let mut viewport_configs = ViewportConfigs {
            viewport_configs: Vec::new(),
        };
        let renderers_json = renderers_config.as_array().unwrap();
        for renderer_config in renderers_json {
            let renderer_id = renderer_config["renderer_id"]
                .as_str()
                .expect("Missing 'renderer_id' field in renderer");

            let viewport_config_json = renderer_config["viewport_config"]
                .as_object()
                .expect("Missing 'viewport_config' field in renderer");

            let viewport_config = ViewportConfig {
                instance_id: renderer_id.to_string(),
                active_camera: viewport_config_json["active_camera"]
                    .as_str()
                    .expect("Missing 'active_camera' field in viewport_config")
                    .to_string(),
            };

            viewport_configs.viewport_configs.push(viewport_config);
        }
        self.add_resource(viewport_configs);

        // Create entities for each actor and their child effectors
        let actors_json = world_config["actors"]
            .as_array()
            .expect("Missing 'actors' field in 'world' config");
        for actor in actors_json {
            let actor_id = actor["actor_name"]
                .as_str()
                .expect("Missing 'actor_name' field in actor");

            info!("=== Loading actor '{}' ===", actor_id);

            let actor_translation = actor["transform"]["position"]
                .as_array()
                .expect("Missing 'transform.position' field in actor");

            let (actor_translation_n, actor_translation_e, actor_translation_d) = (
                actor_translation[0].as_f64().unwrap(),
                actor_translation[1].as_f64().unwrap(),
                actor_translation[2].as_f64().unwrap(),
            );
            let actor_translation_bevy = self.ned_to_bevy_xyz(bevy_math::Vec3::new(
                actor_translation_n as f32,
                actor_translation_e as f32,
                actor_translation_d as f32,
            ));

            let actor_rotation = actor["transform"]["rotation"]
                .as_array()
                .expect("Missing 'transform.rotation' field in actor");
            let actor_rotation_rpy = (
                actor_rotation[0].as_f64().unwrap() as f32,
                actor_rotation[1].as_f64().unwrap() as f32,
                actor_rotation[2].as_f64().unwrap() as f32,
            );

            let _actor_scale = actor["transform"]["scale"]
                .as_array()
                .expect("Missing 'transform.scale' field in actor");

            let actor_quat = aerosim_core::math::quaternion::Quaternion::from_euler_angles(
                [
                    actor_rotation[0].as_f64().unwrap().to_radians(),
                    actor_rotation[1].as_f64().unwrap().to_radians(),
                    actor_rotation[2].as_f64().unwrap().to_radians(),
                ],
                aerosim_core::math::quaternion::RotationType::Extrinsic,
                aerosim_core::math::quaternion::RotationSequence::ZYX,
            );

            let actor_state = ActorState {
                pose: Pose {
                    position: Vector3 {
                        x: actor_translation_n,
                        y: actor_translation_e,
                        z: actor_translation_d,
                    },
                    orientation: Quaternion {
                        w: actor_quat.w(),
                        x: actor_quat.x(),
                        y: actor_quat.y(),
                        z: actor_quat.z(),
                    },
                },
            };

            let actor_bundle = ActorBundle {
                actor_properties: ActorPropertiesComponent {
                    actor_name: actor_id.to_string(),
                    actor_asset: actor["actor_asset"]
                        .as_str()
                        .expect("Missing 'actor_asset' field in actor")
                        .to_string(),
                    parent: actor["parent"]
                        .as_str()
                        .expect("Missing 'parent' field in actor")
                        .to_string(),
                },
                actor_state: ActorStateComponent {
                    state: actor_state,
                    world_coord: WorldCoordinate::from_ned(
                        actor_translation_n,
                        actor_translation_e,
                        actor_translation_d,
                        self.origin_lla.0,
                        self.origin_lla.1,
                        self.origin_lla.2,
                        Ellipsoid::wgs84(),
                    ),
                },
                ecs_transform: bevy_transform::components::Transform {
                    translation: actor_translation_bevy,
                    rotation: self.ned_rpy_to_bevy_quat(actor_rotation_rpy),
                    scale: bevy_math::Vec3::new(1.0, 1.0, 1.0),
                },
            };

            self.add_entity(actor_bundle);

            if let Some(state_topic_value) = actor.pointer("/state/topic") {
                if let Some(state_topic) = state_topic_value.as_str() {
                    self.entity_state_topic_map
                        .insert(state_topic.to_string(), actor_id.to_string());
                }
            }

            let effectors = actor["effectors"].as_array();
            if let Some(effectors) = effectors {
                let mut effectors_component = EffectorsComponent {
                    effectors: Vec::new(),
                };

                for (effector_idx, effector) in effectors.iter().enumerate() {
                    let effector_id = effector["id"]
                        .as_str()
                        .expect("Missing 'id' field in effector");

                    let effector_path = effector["relative_path"]
                        .as_str()
                        .expect("Missing 'relative_path' field in effector");

                    let effector_translation = effector["transform"]["translation"]
                        .as_array()
                        .expect("Missing 'transform.translation' field in effector");

                    let (
                        effector_translation_front,
                        effector_translation_right,
                        effector_translation_down,
                    ) = (
                        effector_translation[0].as_f64().unwrap(),
                        effector_translation[1].as_f64().unwrap(),
                        effector_translation[2].as_f64().unwrap(),
                    );

                    let effector_rotation = effector["transform"]["rotation"]
                        .as_array()
                        .expect("Missing 'transform.rotation' field in effector");

                    let effector_quat =
                        aerosim_core::math::quaternion::Quaternion::from_euler_angles(
                            [
                                effector_rotation[0].as_f64().unwrap().to_radians(),
                                effector_rotation[1].as_f64().unwrap().to_radians(),
                                effector_rotation[2].as_f64().unwrap().to_radians(),
                            ],
                            aerosim_core::math::quaternion::RotationType::Extrinsic,
                            aerosim_core::math::quaternion::RotationSequence::ZYX,
                        );

                    let effector_component = Effector {
                        id: effector_id.to_string(),
                        relative_path: effector_path.to_string(),
                        state: EffectorState {
                            pose: Pose {
                                position: Vector3 {
                                    x: effector_translation_front,
                                    y: effector_translation_right,
                                    z: effector_translation_down,
                                },
                                orientation: Quaternion {
                                    w: effector_quat.w(),
                                    x: effector_quat.x(),
                                    y: effector_quat.y(),
                                    z: effector_quat.z(),
                                },
                            },
                        },
                    };

                    effectors_component.effectors.push(effector_component);

                    let effector_state_topic = effector["state"]["topic"]
                        .as_str()
                        .expect("Missing 'state.topic' field in effector");

                    self.entity_effector_state_topic_map.insert(
                        effector_state_topic.to_string(),
                        (actor_id.to_string(), effector_idx),
                    );
                }

                if let Some(entity) = self.entity_map.get(actor_id).copied() {
                    self.ecs_app
                        .world_mut()
                        .entity_mut(entity)
                        .insert(effectors_component);
                } else {
                    println!("Entity not found for effectors component: {}", actor_id);
                }

                // TODO Add parent-child relationships for effectors to the actor entity
            }

            // Process the flight deck components
            if let Some(flight_deck_json_array) = actor["flight_deck"].as_array() {
                for flight_deck_json_obj in flight_deck_json_array {
                    let flight_deck_id = flight_deck_json_obj["id"]
                        .as_str()
                        .expect("Missing 'id' field in flight_deck object");
                    if flight_deck_id == "primary_flight_display" {
                        let pfd_state_topic = flight_deck_json_obj["state"]["topic"]
                            .as_str()
                            .expect("Missing 'flight_deck[state.topic]' field in actor");

                        self.entity_state_topic_map
                            .insert(pfd_state_topic.to_string(), actor_id.to_string());
                    }

                    // Add PFD component to the actor entity
                    let pfd_component = PrimaryFlightDisplayComponent {
                        pfd_data: PrimaryFlightDisplayData::default(),
                    };

                    if let Some(entity) = self.entity_map.get(actor_id).copied() {
                        self.ecs_app
                            .world_mut()
                            .entity_mut(entity)
                            .insert(pfd_component);
                    } else {
                        println!("Entity not found for actor: {}", actor_id);
                    }
                }
            }

            // Process trajectory visualization components
            if let Some(trajectory_config) = actor.get("trajectory_visualization") {
                if let Some(trajectory_topic) = trajectory_config["topic"].as_str() {
                    self.entity_state_topic_map
                        .insert(trajectory_topic.to_string(), actor_id.to_string());
                }

                // Add trajectory visualization component to the actor entity
                let traj_vis_component = TrajectoryVisualizationComponent {
                    settings: TrajectoryVisualizationSettings::default(),
                    user_defined_waypoints: TrajectoryVisualizationParametersWaypoints::default(),
                    future_trajectory: TrajectoryVisualizationParametersWaypoints::default(),
                };

                if let Some(entity) = self.entity_map.get(actor_id).copied() {
                    self.ecs_app
                        .world_mut()
                        .entity_mut(entity)
                        .insert(traj_vis_component);
                } else {
                    println!("Entity not found for actor: {}", actor_id);
                }
            }
        }

        // Create entities for each sensor
        let sensors_json = world_config["sensors"]
            .as_array()
            .expect("Missing 'sensors' field in 'world' config");
        for sensor in sensors_json {
            let sensor_name = sensor["sensor_name"]
                .as_str()
                .expect("Missing 'sensor_name' field in sensor");

            info!("=== Loading sensor '{}' ===", sensor_name);

            let sensor_translation = sensor["transform"]["translation"]
                .as_array()
                .expect("Missing 'transform.translation' field in sensor");
            let (sensor_translation_n, sensor_translation_e, sensor_translation_d) = (
                sensor_translation[0].as_f64().unwrap(),
                sensor_translation[1].as_f64().unwrap(),
                sensor_translation[2].as_f64().unwrap(),
            );
            let sensor_translation_bevy = self.ned_to_bevy_xyz(bevy_math::Vec3::new(
                sensor_translation_n as f32,
                sensor_translation_e as f32,
                sensor_translation_d as f32,
            ));

            let sensor_rotation = sensor["transform"]["rotation"]
                .as_array()
                .expect("Missing 'transform.rotation' field in sensor");
            let sensor_rotation_rpy = (
                sensor_rotation[0].as_f64().unwrap() as f32,
                sensor_rotation[1].as_f64().unwrap() as f32,
                sensor_rotation[2].as_f64().unwrap() as f32,
            );

            let sensor_type = sensor["type"]
                .as_str()
                .expect("Missing 'type' field in sensor");

            let sensor_quat = aerosim_core::math::quaternion::Quaternion::from_euler_angles(
                [
                    sensor_rotation[0].as_f64().unwrap().to_radians(),
                    sensor_rotation[1].as_f64().unwrap().to_radians(),
                    sensor_rotation[2].as_f64().unwrap().to_radians(),
                ],
                aerosim_core::math::quaternion::RotationType::Extrinsic,
                aerosim_core::math::quaternion::RotationSequence::ZYX,
            );

            let sensor_state = ActorState {
                pose: Pose {
                    position: Vector3 {
                        x: sensor_translation_n,
                        y: sensor_translation_e,
                        z: sensor_translation_d,
                    },
                    orientation: Quaternion {
                        w: sensor_quat.w(),
                        x: sensor_quat.x(),
                        y: sensor_quat.y(),
                        z: sensor_quat.z(),
                    },
                },
            };

            let sensor_actor_bundle = ActorBundle {
                actor_properties: ActorPropertiesComponent {
                    actor_name: sensor_name.to_string(),
                    actor_asset: sensor_type.to_string(),
                    parent: sensor["parent"]
                        .as_str()
                        .expect("Missing 'parent' field in sensor")
                        .to_string(),
                },
                actor_state: ActorStateComponent {
                    state: sensor_state,
                    world_coord: WorldCoordinate::from_ned(
                        sensor_translation_n,
                        sensor_translation_e,
                        sensor_translation_d,
                        self.origin_lla.0,
                        self.origin_lla.1,
                        self.origin_lla.2,
                        Ellipsoid::wgs84(),
                    ),
                },
                ecs_transform: bevy_transform::components::Transform {
                    translation: sensor_translation_bevy,
                    rotation: self.ned_rpy_to_bevy_quat(sensor_rotation_rpy),
                    scale: bevy_math::Vec3::new(1.0, 1.0, 1.0),
                },
            };

            let sensor_parameters = match sensor["type"].as_str().unwrap() {
                "sensors/cameras/rgb_camera" => {
                    let rgb_camera_params = RGBCameraParameters {
                        resolution: (
                            sensor["parameters"]["resolution"][0].as_u64().unwrap() as u32,
                            sensor["parameters"]["resolution"][1].as_u64().unwrap() as u32,
                        ),
                        tick_rate: sensor["parameters"]["tick_rate"].as_f64().unwrap(),
                        fov: sensor["parameters"]["fov"].as_f64().unwrap() as f32,
                        near_clip: sensor["parameters"]["near_clip"].as_f64().unwrap() as f32,
                        far_clip: sensor["parameters"]["far_clip"].as_f64().unwrap() as f32,
                        capture_enabled: sensor["parameters"]["capture_enabled"].as_bool().unwrap(),
                    };
                    SensorParameters::RGBCamera(rgb_camera_params)
                }
                "sensors/depth_sensor" => {
                    let depth_sensor_params = DepthSensorParameters {
                        resolution: (
                            sensor["parameters"]["resolution"][0].as_u64().unwrap() as u32,
                            sensor["parameters"]["resolution"][1].as_u64().unwrap() as u32,
                        ),
                        tick_rate: sensor["parameters"]["tick_rate"].as_f64().unwrap(),
                        fov: sensor["parameters"]["fov"].as_f64().unwrap() as f32,
                        near_clip: sensor["parameters"]["near_clip"].as_f64().unwrap() as f32,
                        far_clip: sensor["parameters"]["far_clip"].as_f64().unwrap() as f32,
                    };
                    SensorParameters::DepthSensor(depth_sensor_params)
                }
                _ => panic!("Unknown sensor type"),
            };

            let sensor_component = SensorComponent {
                sensor_name: sensor_name.to_string(),
                sensor_type: sensor["type"]
                    .as_str()
                    .expect("Missing 'type' field in sensor")
                    .to_string(),
                sensor_parameters,
            };

            self.add_entity(sensor_actor_bundle);

            if let Some(entity) = self.entity_map.get(sensor_name).copied() {
                self.ecs_app
                    .world_mut()
                    .entity_mut(entity)
                    .insert(sensor_component);
            } else {
                println!("Entity not found for sensor: {}", sensor_name);
            }
        }

        // Set parent-child relationships
        let actor_data: Vec<(String, String)> = {
            let world_ref = self.ecs_app.world_mut();
            let mut query = world_ref.query::<(Entity, &ActorPropertiesComponent)>();
            query
                .iter(world_ref)
                .filter_map(|(_, actor_properties)| {
                    if !actor_properties.parent.is_empty() {
                        Some((
                            actor_properties.parent.clone(),
                            actor_properties.actor_name.clone(),
                        ))
                    } else {
                        None
                    }
                })
                .collect()
        };

        for (parent_id, actor_name) in actor_data {
            self.add_child(&parent_id, &actor_name)
                .expect("Failed to add actor as a child.");
        }

        debug!(
            "Entity state topic map (topic: entity): {:?}",
            self.entity_state_topic_map
        );

        info!("Done loading world scene graph.");
    }

    pub fn add_entity(&mut self, bundle: ActorBundle) {
        let entity_id = bundle.actor_properties.actor_name.to_string();
        let spawned_entity = self.ecs_app.world_mut().spawn(bundle).id();
        self.entity_map.insert(entity_id, spawned_entity);
    }

    pub fn add_child(&mut self, parent_id: &str, child_id: &str) -> Result<(), String> {
        let parent_entity = self.entity_map.get(parent_id);
        let child_entity = self.entity_map.get(child_id);
        if let (Some(parent), Some(child)) = (parent_entity, child_entity) {
            let add_child_cmd = AddChild {
                parent: *parent,
                child: *child,
            };

            // Apply the command to the world
            add_child_cmd.apply(self.ecs_app.world_mut());

            Ok(())
        } else {
            Err(format!(
                "Parent or child entity not found for ids: {} {}",
                parent_id, child_id
            ))
        }
    }

    pub fn add_resource(&mut self, resource: impl Resource) {
        self.ecs_app.world_mut().insert_resource(resource);
    }

    pub fn update_world(
        &mut self,
        data_queue: Vec<(TimeStamp, String, SceneGraphStateData)>,
        sim_time: &TimeStamp,
    ) -> Option<serde_json::Value> {
        let sim_time_duration = Duration::new(sim_time.sec as u64, sim_time.nanosec as u32);
        if sim_time_duration - self.last_update_time < self.update_interval {
            return None;
        }
        // debug!("Updating world state at sim time: {:?}", sim_time);

        // Process the data topic queue (may not be in timestamp order)
        // TODO Should this change to be an accumulation of the state data deltas
        // instead of just using the latest?
        let mut data_queue = data_queue;
        // latest_data_topic_map is a map of "topic" -> (timestamp, payload_type, payload)
        let mut latest_data_topic_map: HashMap<String, (TimeStamp, String, String)> =
            HashMap::new();
        for (data_timestamp, topic, scene_graph_state_data) in data_queue.drain(..) {
            // Temporarily deserialize to JsonData only until concrete data types are standardized across components.
            let (payload_type, payload) = match scene_graph_state_data {
                SceneGraphStateData::VehicleState(data) => (
                    "VehicleState".to_string(),
                    serde_json::to_value(data)
                        .expect("Failed to deserialize vehicle state as JSON")
                        .to_string(),
                ),
                SceneGraphStateData::PrimaryFlightDisplayData(data) => (
                    "PrimaryFlightDisplayData".to_string(),
                    serde_json::to_value(data)
                        .expect("Failed to deserialize PFD state as JSON")
                        .to_string(),
                ),
                SceneGraphStateData::TrajectoryVisualization(data) => (
                    "TrajectoryVisualization".to_string(),
                    serde_json::to_value(data)
                        .expect("Failed to deserialize trajectory follower as JSON")
                        .to_string(),
                ),
                SceneGraphStateData::JsonData(data) => (
                    "JsonData".to_string(),
                    data.get_data()
                        .expect("Failed to retrieve JSON data")
                        .to_string(),
                ),
                SceneGraphStateData::EffectorState(data) => (
                    "EffectorState".to_string(),
                    serde_json::to_value(data)
                        .expect("Failed to deserialize effector state as JSON")
                        .to_string(),
                ),
            };

            // Save only the latest time stamp for each topic in queue
            if let Some((existing_timestamp, _existing_payload_type, _existing_payload)) =
                latest_data_topic_map.get(&topic)
            {
                if data_timestamp > *existing_timestamp {
                    latest_data_topic_map.insert(topic, (data_timestamp, payload_type, payload));
                }
            } else {
                latest_data_topic_map.insert(topic, (data_timestamp, payload_type, payload));
            }
        }

        // Process the latest data for each topic
        for (topic, (_timestamp, payload_type, payload)) in latest_data_topic_map {
            // debug!(
            //     "Update world processing topic '{}' with payload: {}",
            //     topic, payload
            // );
            if let Some(entity_id) = self.entity_state_topic_map.get(&topic) {
                if let Some(entity) = self.entity_map.get(entity_id) {
                    // debug!(
                    //     "Updating entity '{}' with state data from topic '{}'",
                    //     entity_id, topic
                    // );
                    match payload_type.as_ref() {
                        "VehicleState" => {
                            let payload_json = serde_json::from_str::<serde_json::Value>(&payload)
                                .expect("Failed to parse VehicleState payload JSON");
                            let state: ActorState =
                                serde_json::from_value(payload_json["state"].clone())
                                    .expect("Failed to parse payload's 'state' JSON");

                            let mut actor_state_component = self
                                .ecs_app
                                .world_mut()
                                .get_mut::<ActorStateComponent>(*entity)
                                .unwrap();

                            actor_state_component.state = state.clone();

                            actor_state_component.world_coord.set_ned(
                                state.pose.position.x,
                                state.pose.position.y,
                                state.pose.position.z,
                            );

                            let bevy_xyz = self.ned_to_bevy_xyz(bevy_math::Vec3::new(
                                state.pose.position.x as f32,
                                state.pose.position.y as f32,
                                state.pose.position.z as f32,
                            ));
                            let bevy_quat = self.ned_quat_to_bevy_quat(bevy_math::Quat::from_xyzw(
                                state.pose.orientation.x as f32,
                                state.pose.orientation.y as f32,
                                state.pose.orientation.z as f32,
                                state.pose.orientation.w as f32,
                            ));

                            let mut ecs_transform_component = self
                                .ecs_app
                                .world_mut()
                                .get_mut::<bevy_transform::components::Transform>(*entity)
                                .unwrap();

                            ecs_transform_component.translation = bevy_xyz;
                            ecs_transform_component.rotation = bevy_quat;
                        }
                        "PrimaryFlightDisplayData" => {
                            let payload_json = serde_json::from_str::<serde_json::Value>(&payload)
                                .expect("Failed to parse PrimaryFlightDisplayData payload JSON");
                            let pfd_data: PrimaryFlightDisplayData =
                                serde_json::from_value(payload_json.clone())
                                    .expect("Failed to parse PFD data payload's JSON");

                            let mut pfd_component = self
                                .ecs_app
                                .world_mut()
                                .get_mut::<PrimaryFlightDisplayComponent>(*entity)
                                .unwrap();
                            pfd_component.pfd_data = pfd_data;
                        }
                        "TrajectoryVisualization" => {
                            let payload_json = serde_json::from_str::<serde_json::Value>(&payload)
                                .expect("Failed to parse TrajectoryVisualization payload JSON");
                            let trajectory_visualization: TrajectoryVisualization =
                                serde_json::from_value(payload_json).expect(
                                    "Failed to parse payload's 'trajectory_visualization' JSON",
                                );
                            let mut trajectory_visualization_component = self
                                .ecs_app
                                .world_mut()
                                .get_mut::<TrajectoryVisualizationComponent>(*entity)
                                .unwrap();

                            let user_defined_waypoints_vec = Self::extract_position_array_from_json(
                                &trajectory_visualization.user_defined_waypoints.waypoints,
                            );
                            let future_trajectory_vec = Self::extract_position_array_from_json(
                                &trajectory_visualization.future_trajectory.waypoints,
                            );

                            trajectory_visualization_component.settings =
                                trajectory_visualization.settings;
                            trajectory_visualization_component
                                .future_trajectory
                                .waypoints = future_trajectory_vec;
                            trajectory_visualization_component
                                .user_defined_waypoints
                                .waypoints = user_defined_waypoints_vec;
                        }
                        "EffectorState" => {
                            // TODO Move EffectorState handling here instead of through the
                            // separate entity_effector_state_topic_map below
                            warn!("EffectorState handling should be processed through entity_state_topic_map instead of here for now.");
                        }
                        _ => {
                            warn!("Unknown payload type: {}", payload_type);
                        }
                    }
                    // TODO Update ecs_transform_component.scale?
                }
            } else if let Some((entity_id, effector_idx)) =
                self.entity_effector_state_topic_map.get(&topic)
            {
                if let Some(entity) = self.entity_map.get(entity_id) {
                    let mut effectors_component = self
                        .ecs_app
                        .world_mut()
                        .get_mut::<EffectorsComponent>(*entity)
                        .unwrap();
                    let effector_component = &mut effectors_component.effectors[*effector_idx];
                    let payload_json = serde_json::from_str::<serde_json::Value>(&payload)
                        .expect("Failed to parse payload JSON");
                    let effector_state: EffectorState = serde_json::from_value(payload_json)
                        .expect("Failed to parse payload's 'state' JSON");
                    effector_component.state = effector_state;
                }
            }
        }

        // Update the ECS world state (run systems to propagate transforms, etc)
        self.ecs_app.update();

        // for (actor_name, entity) in self.entity_map.iter() {
        //     let actor_properties = self
        //         .ecs_app
        //         .world()
        //         .get::<ActorPropertiesComponent>(*entity)
        //         .unwrap();
        //     let actor_global_transform = self
        //         .ecs_app
        //         .world()
        //         .get::<GlobalTransform>(*entity)
        //         .unwrap();
        //     let actor_state_component = self
        //         .ecs_app
        //         .world()
        //         .get::<ActorStateComponent>(*entity)
        //         .unwrap();
        //
        //     let actor_translation = actor_global_transform.translation();
        //     let actor_rotation = actor_global_transform.rotation();
        //     let ned_vec = self.bevy_xyz_to_ned(actor_translation);
        //     let ned_quat = self.bevy_quat_to_ned_quat(actor_rotation);
        //     let actor_scale = actor_global_transform.scale();
        //     // let actor_global_transform_json = json!({
        //     //     "translation": {
        //     //         "x": ned_vec.x,
        //     //         "y": ned_vec.y,
        //     //         "z": ned_vec.z
        //     //     },
        //     //     "orientation": {
        //     //         "w": ned_quat.w,
        //     //         "x": ned_quat.x,
        //     //         "y": ned_quat.y,
        //     //         "z": ned_quat.z
        //     //     },
        //     //     "scale":{
        //     //         "x": actor_scale.x,
        //     //         "y": actor_scale.y,
        //     //         "z": actor_scale.z
        //     //     },
        //     // });
        //     // let actor_world_coord_json = serde_json::to_value(actor_state_component.world_coord)
        //     //     .expect("WorldCoordinate serialization failed");
        // }

        // Publish world state update data
        // TODO: Do this as a query in a system that runs at the end of the update?
        let scene_graph_update_json = self.generate_scene_graph_json();

        self.last_update_time = sim_time_duration;
        Some(scene_graph_update_json)
    }

    pub fn generate_scene_graph_json(&mut self) -> Value {
        let world = self.ecs_app.world_mut();
        let mut actor_properties_query = world.query::<(Entity, &ActorPropertiesComponent)>();
        let mut actor_state_query = world.query::<(Entity, &ActorStateComponent)>();
        let mut sensor_query = world.query::<(Entity, &SensorComponent)>();
        let mut effectors_query = world.query::<(Entity, &EffectorsComponent)>();
        let mut pfd_state_query = world.query::<(Entity, &PrimaryFlightDisplayComponent)>();
        let mut trajectory_query = world.query::<(Entity, &TrajectoryVisualizationComponent)>();

        let mut scene_graph_update_json = json!({});

        let mut entities: HashMap<String, Vec<String>> = HashMap::new();
        let mut actor_properties_map: HashMap<String, Value> = HashMap::new();
        let mut actor_state_map: HashMap<String, Value> = HashMap::new();
        let mut sensor_map: HashMap<String, Value> = HashMap::new();
        let mut effectors_map: HashMap<String, Vec<Value>> = HashMap::new();
        let mut pfd_state_map: HashMap<String, Value> = HashMap::new();
        let mut resources: HashMap<String, Value> = HashMap::new();
        let mut trajectory_map: HashMap<String, Value> = HashMap::new();

        let world_origin_resource = world
            .get_resource::<WorldOrigin>()
            .expect("WorldOrigin resource not found");
        resources.insert("origin".to_string(), json!(world_origin_resource));

        let weather_resource = world
            .get_resource::<Weather>()
            .expect("Weather resource not found");
        resources.insert("weather".to_string(), json!(weather_resource));

        let mut name_to_id_map: HashMap<String, String> = HashMap::new();
        let mut sensor_name_to_id_map: HashMap<String, String> = HashMap::new();

        for (entity, actor_properties) in actor_properties_query.iter(&world) {
            name_to_id_map.insert(
                actor_properties.actor_name.clone(),
                format!("entity_{}", entity.index()),
            );
        }

        for (entity, sensor) in sensor_query.iter(&world) {
            sensor_name_to_id_map.insert(
                sensor.sensor_name.clone(),
                format!("entity_{}", entity.index()),
            );
        }

        let viewport_configs = world
            .get_resource::<ViewportConfigs>()
            .expect("ViewportConfigs resource not found");

        let viewport_configs_json: Vec<_> = viewport_configs
            .viewport_configs
            .iter()
            .map(|vc| {
                json!({
                    "renderer_instance": vc.instance_id,
                    "active_camera": sensor_name_to_id_map
                        .get(&vc.active_camera)
                        .cloned()
                        .unwrap_or_default(),
                })
            })
            .collect();

        resources.insert("viewport_configs".to_string(), json!(viewport_configs_json));

        for (entity, actor_properties) in actor_properties_query.iter(&world) {
            let key = format!("entity_{}", entity.index());
            let parent_entity_id = name_to_id_map
                .get(&actor_properties.parent)
                .cloned()
                .unwrap_or_default();
            let value = json!({
                "actor_name": actor_properties.actor_name,
                "actor_asset": actor_properties.actor_asset,
                "parent": parent_entity_id,
            });

            actor_properties_map.insert(key.clone(), value);
            entities
                .entry(key.clone())
                .or_default()
                .push("actor_properties".to_string());
        }

        for (entity, actor_state) in actor_state_query.iter(&world) {
            let key = format!("entity_{}", entity.index());
            let world_coordinate = &actor_state.world_coord;
            let world_coordinate_json = json!({
                "ned": {
                    "north": world_coordinate.ned.0,
                    "east": world_coordinate.ned.1,
                    "down": world_coordinate.ned.2,
                },
                "lla": {
                    "latitude": world_coordinate.lla.0,
                    "longitude": world_coordinate.lla.1,
                    "altitude": world_coordinate.lla.2,
                },
                "ecef": {
                    "x": world_coordinate.ecef.0,
                    "y": world_coordinate.ecef.1,
                    "z": world_coordinate.ecef.2,
                },
                "cartesian": {
                    "x": world_coordinate.cartesian.0,
                    "y": world_coordinate.cartesian.1,
                    "z": world_coordinate.cartesian.2,
                },
                "origin_lla": {
                    "latitude": world_coordinate.origin_lla.0,
                    "longitude": world_coordinate.origin_lla.1,
                    "altitude": world_coordinate.origin_lla.2,
                },
                "ellipsoid": {
                    "equatorial_radius": world_coordinate.ellipsoid.equatorial_radius,
                    "flattening_factor": world_coordinate.ellipsoid.flattening_factor,
                    "polar_radius": world_coordinate.ellipsoid.polar_radius,
                }
            });

            let pose = &actor_state.state.pose;
            let pose_json = json!({
                "transform": {
                    "position": {
                        "x": pose.position.x,
                        "y": pose.position.y,
                        "z": pose.position.z,
                    },
                    "orientation": {
                        "w": pose.orientation.w,
                        "x": pose.orientation.x,
                        "y": pose.orientation.y,
                        "z": pose.orientation.z,
                    },
                    "scale": {
                        "x": 1.0,
                        "y": 1.0,
                        "z": 1.0,
                    }
                }
            });

            let value = json!({
                 "pose": pose_json,
                 "world_coordinate": world_coordinate_json,
            });

            actor_state_map.insert(key.clone(), value);
            entities
                .entry(key.clone())
                .or_default()
                .push("actor_state".to_string());
        }

        for (entity, sensor) in sensor_query.iter(&world) {
            let key = format!("entity_{}", entity.index());
            let value = json!({
                "sensor_name": sensor.sensor_name,
                "sensor_type": sensor.sensor_type,
                "sensor_parameters": sensor.sensor_parameters,
            });

            sensor_map.insert(key.clone(), value);
            entities
                .entry(key.clone())
                .or_default()
                .push("sensor".to_string());
        }

        for (entity, effectors) in effectors_query.iter(&world) {
            let key = format!("entity_{}", entity.index());

            let mut effector_jsons = Vec::new();
            for effector in effectors.effectors.iter() {
                let effector_id = effector.id.clone();
                let effector_path = effector.relative_path.clone();
                let effector_pose = effector.state.pose.clone();

                let pose_json = json!({
                    "transform": {
                        "position": {
                            "x": effector_pose.position.x,
                            "y": effector_pose.position.y,
                            "z": effector_pose.position.z,
                        },
                        "orientation": {
                            "w": effector_pose.orientation.w,
                            "x": effector_pose.orientation.x,
                            "y": effector_pose.orientation.y,
                            "z": effector_pose.orientation.z,
                        },
                        "scale": {
                            "x": 1.0,
                            "y": 1.0,
                            "z": 1.0,
                        }
                    }
                });

                let effector_json = json!({
                    "effector_id": effector_id,
                    "relative_path": effector_path,
                    "pose": pose_json,
                });

                effector_jsons.push(effector_json);
            }

            effectors_map.insert(key.clone(), effector_jsons);
            entities
                .entry(key.clone())
                .or_default()
                .push("effectors".to_string());
        }

        for (entity, pfd_state) in pfd_state_query.iter(&world) {
            let key = format!("entity_{}", entity.index());
            let value = serde_json::to_value(pfd_state).expect("Failed to serialize PFD state");
            pfd_state_map.insert(key.clone(), value);
            entities
                .entry(key.clone())
                .or_default()
                .push("primary_flight_display_state".to_string());
        }

        for (entity, trajectory) in trajectory_query.iter(&world) {
            let key = format!("entity_{}", entity.index());
            let value = json!({
                "parameters": trajectory,
            });

            trajectory_map.insert(key.clone(), value);
            entities
                .entry(key.clone())
                .or_default()
                .push("trajectory".to_string());
        }

        scene_graph_update_json["entities"] = json!(entities);
        scene_graph_update_json["components"]["actor_properties"] = json!(actor_properties_map);
        scene_graph_update_json["components"]["actor_state"] = json!(actor_state_map);
        scene_graph_update_json["components"]["sensor"] = json!(sensor_map);
        scene_graph_update_json["components"]["effectors"] = json!(effectors_map);
        scene_graph_update_json["components"]["primary_flight_display_state"] =
            json!(pfd_state_map);
        scene_graph_update_json["resources"] = json!(resources);
        scene_graph_update_json["components"]["trajectory"] = json!(trajectory_map);

        scene_graph_update_json
    }

    // Example of a queried system that can be parallelized
    pub fn update_sim_coordinates(mut query: Query<(&mut ActorStateComponent, &GlobalTransform)>) {
        // // Series iteration
        // for (mut actor, transform) in query.iter_mut() {
        //     let translation_vec = transform.translation();
        //     actor.state.set_ned(
        //         translation_vec.x.into(),
        //         translation_vec.y.into(),
        //         translation_vec.z.into(),
        //     );
        // }

        // Parallel iteration through the query result entities
        query
            .par_iter_mut()
            .for_each(|(mut actor_state, transform)| {
                let translation_vec = transform.translation();
                actor_state.world_coord.set_ned(
                    translation_vec.x.into(),
                    translation_vec.y.into(),
                    translation_vec.z.into(),
                );
            });
        // debug!("Updated sim coordinates");
    }

    // // Example of 'exclusive system' with full world ECS access, but can't be parallelized
    // pub fn update_sim_coordinates_exclusive(world: &mut World) {
    //     let mut query = world.query::<(&mut ActorComponent, &GlobalTransform)>();
    //     for (mut actor, transform) in query.iter_mut(world) {
    //         let translation_vec = transform.translation();
    //         actor.state.set_ned(
    //             translation_vec.x.into(),
    //             translation_vec.y.into(),
    //             translation_vec.z.into(),
    //         );
    //     }
    //     println!("Updated sim coordinates with exclusive world access");
    // }

    fn extract_position_array_from_json(json_array: &String) -> Vec<(f32, f32, f32)> {
        if let Some(start) = json_array.find('[') {
            if let Some(end) = json_array.rfind(']') {
                let json_str = &&json_array[start..=end];
                let waypoints: serde_json::Result<Vec<(f32, f32, f32)>> =
                    serde_json::from_str(json_str);
                match waypoints {
                    Ok(points) => points,
                    Err(err) => {
                        eprintln!("Failed to read waypoints: {:?}", err);
                        vec![]
                    }
                }
            } else {
                vec![]
            }
        } else {
            vec![]
        }
    }
}

#[cfg(test)]
mod tests {
    // use super::*;
    // use bevy_ecs::world::CommandQueue;
    // use bevy_transform::components::Transform;

    // fn get_translation(world: &World, entity: Entity) -> bevy_math::Vec3 {
    //     world.get::<Transform>(entity).unwrap().translation
    // }

    // fn get_global_translation(world: &World, entity: Entity) -> bevy_math::Vec3 {
    //     world.get::<GlobalTransform>(entity).unwrap().translation()
    // }

    // #[test]
    // fn transform_tree_with_schedule() {
    //     println!("------- Build scene graph using world schedule -------");
    //     #[derive(bevy_ecs::schedule::ScheduleLabel, Hash, PartialEq, Eq, Debug, Clone)]
    //     struct AeroSimSchedule;

    //     let mut world = World::default();
    //     let mut schedule = Schedule::new(AeroSimSchedule);
    //     schedule.add_systems((
    //         sync_simple_transforms,
    //         propagate_transforms,
    //         SceneGraph::update_sim_coordinates
    //             .after(sync_simple_transforms)
    //             .after(propagate_transforms),
    //     ));

    //     // Create a parent entity with two children
    //     let origin_lla = (0.0, 0.0, 0.0);
    //     let parent_spawn_pos: (f32, f32, f32) = (1.0, 0.0, 0.0);
    //     let child1_spawn_pos: (f32, f32, f32) = (0.0, 2.0, 0.0);
    //     let child2_spawn_pos: (f32, f32, f32) = (0.0, 0.0, 3.0);
    //     let parent;
    //     let mut children = Vec::new();
    //     let mut parent_pos;
    //     let mut parent_global_pos;
    //     let mut child1_pos;
    //     let mut child1_global_pos;
    //     let mut child2_pos;
    //     let mut child2_global_pos;

    //     let mut command_queue = CommandQueue::default();

    //     {
    //         // Spawn parent
    //         let mut commands = Commands::new(&mut command_queue, &world);
    //         parent = commands
    //             .spawn(ActorBundle {
    //                 actor_properties: ActorPropertiesComponent {
    //                     id: "actor1".to_string(),
    //                     actor_type: "parent".to_string(),
    //                     usd: "usd".to_string(),
    //                 },
    //                 actor_state: ActorStateComponent {
    //                     state: ActorState::with_timestamp(aerosim_data::types::TimeStamp {
    //                         sec: 0,
    //                         nanosec: 0,
    //                     }),
    //                     world_coord: WorldCoordinate::from_ned(
    //                         parent_spawn_pos.0.into(),
    //                         parent_spawn_pos.1.into(),
    //                         parent_spawn_pos.2.into(),
    //                         origin_lla.0,
    //                         origin_lla.1,
    //                         origin_lla.2,
    //                         Ellipsoid::wgs84(),
    //                     ),
    //                 },
    //                 ecs_transform: Transform::from_xyz(
    //                     parent_spawn_pos.0,
    //                     parent_spawn_pos.1,
    //                     parent_spawn_pos.2,
    //                 ),
    //             })
    //             .with_children(|parent| {
    //                 children.push(
    //                     parent
    //                         .spawn(ActorBundle {
    //                             actor_properties: ActorPropertiesComponent {
    //                                 id: "actor2".to_string(),
    //                                 actor_type: "child".to_string(),
    //                                 usd: "usd".to_string(),
    //                             },
    //                             actor_state: ActorStateComponent {
    //                                 state: ActorState::with_timestamp(
    //                                     aerosim_data::types::TimeStamp { sec: 0, nanosec: 0 },
    //                                 ),
    //                                 world_coord: WorldCoordinate::from_ned(
    //                                     child1_spawn_pos.0.into(),
    //                                     child1_spawn_pos.1.into(),
    //                                     child1_spawn_pos.2.into(),
    //                                     origin_lla.0,
    //                                     origin_lla.1,
    //                                     origin_lla.2,
    //                                     Ellipsoid::wgs84(),
    //                                 ),
    //                             },
    //                             ecs_transform: Transform::from_xyz(
    //                                 child1_spawn_pos.0,
    //                                 child1_spawn_pos.1,
    //                                 child1_spawn_pos.2,
    //                             ),
    //                         })
    //                         .id(),
    //                 );
    //                 children.push(
    //                     parent
    //                         .spawn(ActorBundle {
    //                             actor_properties: ActorPropertiesComponent {
    //                                 id: "actor3".to_string(),
    //                                 actor_type: "child".to_string(),
    //                                 usd: "usd".to_string(),
    //                             },
    //                             actor_state: ActorStateComponent {
    //                                 state: ActorState::with_timestamp(
    //                                     aerosim_data::types::TimeStamp { sec: 0, nanosec: 0 },
    //                                 ),
    //                                 world_coord: WorldCoordinate::from_ned(
    //                                     child2_spawn_pos.0.into(),
    //                                     child2_spawn_pos.1.into(),
    //                                     child2_spawn_pos.2.into(),
    //                                     origin_lla.0,
    //                                     origin_lla.1,
    //                                     origin_lla.2,
    //                                     Ellipsoid::wgs84(),
    //                                 ),
    //                             },
    //                             ecs_transform: Transform::from_xyz(
    //                                 child2_spawn_pos.0,
    //                                 child2_spawn_pos.1,
    //                                 child2_spawn_pos.2,
    //                             ),
    //                         })
    //                         .id(),
    //                 );
    //             })
    //             .id();

    //         // Run the schedule systems to update the transform tree
    //         command_queue.apply(&mut world);
    //         schedule.run(&mut world);

    //         // Print transforms of the entities
    //         parent_pos = get_translation(&world, parent);
    //         parent_global_pos = get_global_translation(&world, parent);
    //         child1_pos = get_translation(&world, children[0]);
    //         child1_global_pos = get_global_translation(&world, children[0]);
    //         child2_pos = get_translation(&world, children[1]);
    //         child2_global_pos = get_global_translation(&world, children[1]);

    //         let child2_ned = world
    //             .get::<ActorStateComponent>(children[1])
    //             .unwrap()
    //             .world_coord
    //             .ned();

    //         println!(
    //             "Parent {:?} translation {:?}, global translation {:?}",
    //             parent, parent_pos, parent_global_pos
    //         );
    //         println!(
    //             "Child1 {:?} translation {:?}, global translation {:?}",
    //             children[0], child1_pos, child1_global_pos
    //         );
    //         println!(
    //             "Child2 {:?} translation {:?}, global translation {:?}, world coord NED {:?}",
    //             children[1], child2_pos, child2_global_pos, child2_ned
    //         );

    //         assert!(child1_global_pos == parent_pos + child1_pos);
    //         assert!(child2_global_pos == parent_pos + child2_pos);
    //     }

    //     {
    //         // Change child2's parent to be child1
    //         let add_child_cmd = AddChild {
    //             parent: children[0],
    //             child: children[1],
    //         };

    //         // Apply the command to the world
    //         // let mut commands = Commands::new(&mut command_queue, &world);
    //         // commands.queue(add_child_cmd);

    //         // Run the schedule systems to update the transform tree
    //         // command_queue.push(add_child_cmd);
    //         // command_queue.apply(&mut world);

    //         add_child_cmd.apply(&mut world);
    //         schedule.run(&mut world);
    //     }

    //     // Print transforms of the entities
    //     println!("After changing child2's parent to child1");
    //     parent_pos = get_translation(&world, parent);
    //     parent_global_pos = get_global_translation(&world, parent);
    //     child1_pos = get_translation(&world, children[0]);
    //     child1_global_pos = get_global_translation(&world, children[0]);
    //     child2_pos = get_translation(&world, children[1]);
    //     child2_global_pos = get_global_translation(&world, children[1]);

    //     let child2_ned = world
    //         .get::<ActorStateComponent>(children[1])
    //         .unwrap()
    //         .world_coord
    //         .ned();

    //     println!(
    //         "Parent {:?} translation {:?}, global translation {:?}",
    //         parent, parent_pos, parent_global_pos
    //     );
    //     println!(
    //         "Child1 {:?} translation {:?}, global translation {:?}",
    //         children[0], child1_pos, child1_global_pos
    //     );
    //     println!(
    //         "Child2 {:?} translation {:?}, global translation {:?}, world coord NED {:?}",
    //         children[1], child2_pos, child2_global_pos, child2_ned
    //     );

    //     assert!(child1_global_pos == parent_pos + child1_pos);
    //     assert!(child2_global_pos == parent_pos + child1_pos + child2_pos);
    //     assert!(child2_global_pos == child1_global_pos + child2_pos);
    // }

    // #[test]
    // fn transform_tree_with_app() {
    //     println!("------- Build scene graph using world app -------");
    //     let mut app = App::new();
    //     app.add_systems(Update, (sync_simple_transforms, propagate_transforms));
    //     app.add_systems(PostUpdate, SceneGraph::update_sim_coordinates);

    //     // Create a parent entity with two children
    //     let origin_lla = (0.0, 0.0, 0.0);
    //     let parent_spawn_pos: (f32, f32, f32) = (1.0, 0.0, 0.0);
    //     let child1_spawn_pos: (f32, f32, f32) = (0.0, 2.0, 0.0);
    //     let child2_spawn_pos: (f32, f32, f32) = (0.0, 0.0, 3.0);
    //     let mut children = Vec::new();
    //     let parent =
    //         app.world_mut()
    //             .spawn(ActorBundle {
    //                 actor_properties: ActorPropertiesComponent {
    //                     id: "actor1".to_string(),
    //                     actor_type: "parent".to_string(),
    //                     usd: "usd".to_string(),
    //                 },
    //                 actor_state: ActorStateComponent {
    //                     state: ActorState::with_timestamp(aerosim_data::types::TimeStamp {
    //                         sec: 0,
    //                         nanosec: 0,
    //                     }),
    //                     world_coord: WorldCoordinate::from_ned(
    //                         parent_spawn_pos.0.into(),
    //                         parent_spawn_pos.1.into(),
    //                         parent_spawn_pos.2.into(),
    //                         origin_lla.0,
    //                         origin_lla.1,
    //                         origin_lla.2,
    //                         Ellipsoid::wgs84(),
    //                     ),
    //                 },
    //                 ecs_transform: Transform::from_xyz(
    //                     parent_spawn_pos.0,
    //                     parent_spawn_pos.1,
    //                     parent_spawn_pos.2,
    //                 ),
    //             })
    //             .with_children(|parent| {
    //                 children.push(
    //                     parent
    //                         .spawn(ActorBundle {
    //                             actor_properties: ActorPropertiesComponent {
    //                                 id: "actor2".to_string(),
    //                                 actor_type: "child".to_string(),
    //                                 usd: "usd".to_string(),
    //                             },
    //                             actor_state: ActorStateComponent {
    //                                 state: ActorState::with_timestamp(
    //                                     aerosim_data::types::TimeStamp { sec: 0, nanosec: 0 },
    //                                 ),
    //                                 world_coord: WorldCoordinate::from_ned(
    //                                     child1_spawn_pos.0.into(),
    //                                     child1_spawn_pos.1.into(),
    //                                     child1_spawn_pos.2.into(),
    //                                     origin_lla.0,
    //                                     origin_lla.1,
    //                                     origin_lla.2,
    //                                     Ellipsoid::wgs84(),
    //                                 ),
    //                             },
    //                             ecs_transform: Transform::from_xyz(
    //                                 child1_spawn_pos.0,
    //                                 child1_spawn_pos.1,
    //                                 child1_spawn_pos.2,
    //                             ),
    //                         })
    //                         .id(),
    //                 );
    //                 children.push(
    //                     parent
    //                         .spawn(ActorBundle {
    //                             actor_properties: ActorPropertiesComponent {
    //                                 id: "actor3".to_string(),
    //                                 actor_type: "child".to_string(),
    //                                 usd: "usd".to_string(),
    //                             },
    //                             actor_state: ActorStateComponent {
    //                                 state: ActorState::with_timestamp(
    //                                     aerosim_data::types::TimeStamp { sec: 0, nanosec: 0 },
    //                                 ),
    //                                 world_coord: WorldCoordinate::from_ned(
    //                                     child2_spawn_pos.0.into(),
    //                                     child2_spawn_pos.1.into(),
    //                                     child2_spawn_pos.2.into(),
    //                                     origin_lla.0,
    //                                     origin_lla.1,
    //                                     origin_lla.2,
    //                                     Ellipsoid::wgs84(),
    //                                 ),
    //                             },
    //                             ecs_transform: Transform::from_xyz(
    //                                 child2_spawn_pos.0,
    //                                 child2_spawn_pos.1,
    //                                 child2_spawn_pos.2,
    //                             ),
    //                         })
    //                         .id(),
    //                 );
    //             })
    //             .id();

    //     // Run the app systems to update the transform tree
    //     app.update();

    //     // Print transforms of the entities
    //     let mut parent_pos = get_translation(app.world(), parent);
    //     let mut parent_global_pos = get_global_translation(app.world(), parent);
    //     let mut child1_pos = get_translation(app.world(), children[0]);
    //     let mut child1_global_pos = get_global_translation(app.world(), children[0]);
    //     let mut child2_pos = get_translation(app.world(), children[1]);
    //     let mut child2_global_pos = get_global_translation(app.world(), children[1]);

    //     let child2_ned = app
    //         .world()
    //         .get::<ActorStateComponent>(children[1])
    //         .unwrap()
    //         .world_coord
    //         .ned();

    //     println!(
    //         "Parent {:?} translation {:?}, global translation {:?}",
    //         parent, parent_pos, parent_global_pos
    //     );
    //     println!(
    //         "Child1 {:?} translation {:?}, global translation {:?}",
    //         children[0], child1_pos, child1_global_pos
    //     );
    //     println!(
    //         "Child2 {:?} translation {:?}, global translation {:?}, world coord NED {:?}",
    //         children[1], child2_pos, child2_global_pos, child2_ned
    //     );

    //     assert!(child1_global_pos == parent_pos + child1_pos);
    //     assert!(child2_global_pos == parent_pos + child2_pos);

    //     // Change child2's parent to be child1
    //     {
    //         let add_child_cmd = AddChild {
    //             parent: children[0],
    //             child: children[1],
    //         };

    //         // Apply the command to the world
    //         add_child_cmd.apply(app.world_mut());

    //         // Run the app systems to update the transform tree
    //         app.update();
    //     }

    //     // Print transforms of the entities
    //     println!("After changing child2's parent to child1");
    //     parent_pos = get_translation(app.world(), parent);
    //     parent_global_pos = get_global_translation(app.world(), parent);
    //     child1_pos = get_translation(app.world(), children[0]);
    //     child1_global_pos = get_global_translation(app.world(), children[0]);
    //     child2_pos = get_translation(app.world(), children[1]);
    //     child2_global_pos = get_global_translation(app.world(), children[1]);

    //     let child2_ned = app
    //         .world()
    //         .get::<ActorStateComponent>(children[1])
    //         .unwrap()
    //         .world_coord
    //         .ned();

    //     println!(
    //         "Parent {:?} translation {:?}, global translation {:?}",
    //         parent, parent_pos, parent_global_pos
    //     );
    //     println!(
    //         "Child1 {:?} translation {:?}, global translation {:?}",
    //         children[0], child1_pos, child1_global_pos
    //     );
    //     println!(
    //         "Child2 {:?} translation {:?}, global translation {:?}, world coord NED {:?}",
    //         children[1], child2_pos, child2_global_pos, child2_ned
    //     );

    //     assert!(child1_global_pos == parent_pos + child1_pos);
    //     assert!(child2_global_pos == parent_pos + child1_pos + child2_pos);
    //     assert!(child2_global_pos == child1_global_pos + child2_pos);
    // }
}
