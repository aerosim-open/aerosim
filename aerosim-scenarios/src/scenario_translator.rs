use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json;

use crate::Scenario;
use crate::ActorScenarioData;

#[derive(Serialize, Deserialize)]
struct Config {
    description: String,
    clock: Clock,
    orchestrator: Orchestrator,
    world: World,
    renderers: Vec<Renderer>,
    fmu_models: Vec<FmuModel>,
}

#[derive(Serialize, Deserialize)]
struct Clock {
    step_size_ms: u32,
    pace_1x_scale: bool,
}

#[derive(Serialize, Deserialize)]
struct Orchestrator {
    sync_topics: Vec<SyncTopic>,
}

#[derive(Serialize, Deserialize)]
struct SyncTopic {
    topic: String,
    interval_ms: u32,
}

#[derive(Serialize, Deserialize)]
struct World {
    update_interval_ms: u32,
    origin: Origin,
    actors: Vec<Actor>,
    sensor_setup: Vec<String>,
}

#[derive(Serialize, Deserialize)]
struct Origin {
    latitude: f32,
    longitude: f32,
    altitude: f32,
}

#[derive(Serialize, Deserialize)]
struct Actor {
    id: String,
    r#type: String,
    usd: String,
    description: String,
    transform: Transform,
    state: State,
    effectors: Vec<Effector>,
}

#[derive(Serialize, Deserialize)]
struct Transform {
    translation: Vec<f64>,
    rotation: Vec<f64>,
    scale: Vec<f64>,
}

#[derive(Serialize, Deserialize)]
struct State {
    msg_type: String,
    topic: String,
}

#[derive(Serialize, Deserialize)]
struct Effector {
    id: String,
    r#type: String,
    usd: String,
    transform: Transform,
    state: State,
}

#[derive(Serialize, Deserialize)]
struct Renderer {
    renderer_id: String,
    role: String,
    sensors: Vec<Sensor>,
}

#[derive(Serialize, Deserialize)]
struct Sensor {
    sensor_name: String,
    r#type: String,
    parent: String,
    tick_rate: f64,
    transform: Transform,
    // TODO 'parameters'
}

#[derive(Serialize, Deserialize)]
struct FmuModel {
    id: String,
    fmu_model_path: String,
    component_type: String,
    component_input_topics: Vec<ComponentTopic>,
    component_output_topics: Vec<ComponentTopic>,
    fmu_aux_input_mapping: serde_json::Value,
    fmu_aux_output_mapping: serde_json::Value,
    fmu_initial_vals: serde_json::Value,
}

#[derive(Serialize, Deserialize)]
struct ComponentTopic {
    msg_type: String,
    topic: String,
}

#[pyclass]
pub struct ConfigGenerator
{
    #[pyo3(get, set)]
    base_scenario: Scenario,
}

impl ConfigGenerator {

    fn is_vehicle(actor_type: String) -> bool {
        if actor_type == "vehicle" {
            return true;
        }
        else if actor_type == "airplane" {
            return true;
        }
        else if actor_type == "helicopter" {
            return true;
        }
        else if actor_type == "vtol" {
            return true;
        }
        else if actor_type == "aeroplane" {
            return true;
        }
        else if actor_type == "drone" {
            return true;
        }
        else {
            return false;
        }
    }

    fn generate_state_topic(actorid: String) -> String {
        format!("aerosim.{}.vehicle_state", actorid)
    }

    fn generate_state_type(actor_type: String) -> String {
        if Self::is_vehicle(actor_type.clone()) {
            return "aerosim::types::VehicleState".to_string();
        }
        else {
            return "aerosim::types::JsonData".to_string();
        }
    }

    fn generate_sync_topics(actorid: String) -> Vec<SyncTopic> {
        let mut topics = Vec::new();
        // topics.push(SyncTopic{topic: format!("aerosim.{}.flight_control_command", actorid), interval_ms: 20});
        // topics.push(SyncTopic{topic: format!("aerosim.{}.aircraft_effector_command", actorid), interval_ms: 20});
        topics.push(SyncTopic{topic: format!("aerosim.{}.vehicle_state", actorid), interval_ms: 20});
        topics
    }

    fn generate_topics(actorid: String) -> Vec<(String, String)>{
        let mut topics = Vec::new();
        // topics.push(format!("aerosim.{}.autopilot_command", actorid));
        // topics.push(format!("aerosim.{}.flight_control_command", actorid));
        // topics.push(format!("aerosim.{}.aircraft_effector_command", actorid));
        topics.push((format!("aerosim.{}.vehicle_state", actorid), "aerosim::types::VehicleState".to_string()));
        // topics.push(format!("aerosim.{}.effector1.state", actorid));
        // topics.push(format!("aerosim.{}.jsbsim_dynamics_model.aux_out", actorid));
        topics
    }

    fn generate_actor(actordata : ActorScenarioData) -> Actor {
        let actorid = actordata.actor_id.clone();
        let actortype = actordata.actor_type.clone();
        let actor : Actor = Actor {
            id: actorid.clone(),
            r#type: actortype.clone(),
            usd: actordata.usd.unwrap(),
            description: actordata.description.unwrap(),
            transform: Transform {
                translation: (actordata.transform.clone().unwrap().translation.to_vec()),
                rotation: actordata.transform.clone().unwrap().rotation.to_euler_vec(),
                scale: (actordata.transform.clone().unwrap().scale.unwrap().to_vec()),
            },
            state: State {
                msg_type: Self::generate_state_type(actortype),
                topic: Self::generate_state_topic(actorid),
            },
            effectors: Vec::new(),
        };
        actor
    }

    fn generate_fmu_model(actordata : ActorScenarioData ) -> FmuModel {
        let actorid = actordata.actor_id.clone();
        let fmumodel = FmuModel {
            id: format!("trajectory_follower_{}", actorid),
            fmu_model_path: "fmu/trajectory_follower_fmu_model.fmu".to_string(),
            component_type: "controller".to_string(),
            component_input_topics: vec![],
            component_output_topics: vec![
                ComponentTopic {
                    msg_type: "aerosim::types::VehicleState".to_string(),
                    topic: format!("aerosim.{}.vehicle_state", actorid),
                },
            ],
            fmu_aux_input_mapping: serde_json::json!({}),
            fmu_aux_output_mapping: serde_json::json!({}),
            fmu_initial_vals: serde_json::json!({
                "coordinates_root_dir": "trajectories/scenarios_generated/",
                "coordinates_script":  format!("{}.json", actorid),
                "use_linear_interpolation": false,
                "time_step_in_seconds": 0.01,
                "origin_latitude": actordata.latitude,
                "origin_longitude": actordata.longitude,
                "origin_altitude": actordata.height,
                "curvature_roll_factor": 1.0,
                "visualize_generated_waypoints_ahead": false,
                "visualize_generated_waypoints_behind": false,
                "visualize_user_defined_waypoints": false,
                "number_of_waypoints_ahead": 2
            }),
        };
        fmumodel
    }
}

#[pymethods]
impl ConfigGenerator {
    #[new]
    fn new(base: Scenario) -> Self {
        Self { base_scenario: base }
    }


    fn generate_json(&self) -> PyResult<String> {
        let mut topics = Vec::new();
        let mut actors = Vec::new();
        let mut sync_topics = Vec::new();
        let mut renderers = Vec::new();
        let mut fmu_models = Vec::new();

        for actor_data in self.base_scenario.actors.iter() {
            if Self::is_vehicle(actor_data.actor_type.clone()) {
                topics.append(&mut Self::generate_topics(actor_data.actor_id.clone()));
                sync_topics.append(&mut Self::generate_sync_topics(actor_data.actor_id.clone()));
                fmu_models.push(Self::generate_fmu_model(actor_data.clone()));
            }
            actors.push(Self::generate_actor(actor_data.clone()));
        }

        // TODO Populate renderers and sensors
        renderers.push(Renderer {
            renderer_id: "0".to_string(),
            role: "primary".to_string(),
            sensors: vec![],
        });

        let config = Config {
            description: self.base_scenario.description.clone(),
            clock: Clock {
                step_size_ms: 20,
                pace_1x_scale: true,
            },
            orchestrator: Orchestrator {
                sync_topics: sync_topics,
            },
            world: World {
                update_interval_ms: 20,
                origin: Origin {
                    latitude: self.base_scenario.latitude,
                    longitude: self.base_scenario.longitude,
                    altitude: self.base_scenario.height ,
                },
                actors: actors,
                sensor_setup: vec![],
            },
            renderers: renderers,
            fmu_models: fmu_models,
        };

        let json_string = serde_json::to_string_pretty(&config).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        Ok(json_string)
    }
}
