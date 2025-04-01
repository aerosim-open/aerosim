use ::log::{debug, error, info, warn};

use pyo3::prelude::*;

use std::collections::HashSet;
use std::sync::{
    mpsc::{self, Receiver, Sender, TryRecvError},
    Arc, Mutex,
};
use std::time::Duration;
use std::{thread, thread::JoinHandle};

use serde_json::json;

use crate::{
    data_manager::DataManager,
    logging::warn_rate_limited,
    scene_graph::{SceneGraph, SceneGraphStateData},
    sim_clock::SimClock,
};
use aerosim_data::{
    middleware::{Middleware, MiddlewareEnum, MiddlewareRaw, MiddlewareRegistry, Serializer},
    types::{JsonData, TimeStamp},
};

// -------------------------------------------------------------------------
// Orchestrator class

#[pyclass]
pub struct Orchestrator {
    sim_config: serde_json::Value,
    orchestrator_thread_handle: Option<JoinHandle<()>>,
    orchestrator_thread_tx_stop: Option<Sender<bool>>,
    simclock: Option<Arc<SimClock>>,
    data_manager: Option<Arc<DataManager>>,
    middleware: Option<Arc<MiddlewareEnum>>,
    runtime: Option<tokio::runtime::Runtime>,
    scene_graph_data_queue: Arc<Mutex<Vec<(TimeStamp, String, SceneGraphStateData)>>>,
}

#[pymethods]
impl Orchestrator {
    #[new]
    fn __new__() -> Self {
        let orchestrator = Orchestrator {
            sim_config: Default::default(),
            orchestrator_thread_handle: None,
            orchestrator_thread_tx_stop: None,
            simclock: None,
            data_manager: None,
            middleware: None,
            runtime: None,
            scene_graph_data_queue: Arc::new(Mutex::new(Vec::new())),
        };
        orchestrator.configure_logger();
        orchestrator
    }

    fn configure_logger(&self) {
        let load_logger_with_default_config = |_| {
            warn!("Couldn't load from log4rs.yaml file, using defaults instead.");
            // If loading from config yaml fails, load from this JSON as a default config
            let cfg = serde_json::json!({
                "refresh_rate": "30 seconds",
                "root" : {
                    "appenders": ["stdout", "simlog"],
                    "level": "trace"
                },
                "appenders": {
                    "stdout": {
                        "kind": "console",
                        "filters": [
                            {
                                "kind": "threshold",
                                "level": "info"
                            }
                        ]
                    },
                    "simlog": {
                        "kind": "file",
                        "path": "logs/aerosim.log",
                        "encoder": {
                            "pattern": "{d} - {m}{n}"
                        }
                    }
                }
            });
            let config =
                serde_json::from_str::<log4rs::config::RawConfig>(&cfg.to_string()).unwrap();
            log4rs::init_raw_config(config)
        };

        let _ = log4rs::init_file("log4rs.yaml", Default::default())
            .or_else(load_logger_with_default_config);
    }

    fn load(&mut self, sim_config_json_str: String) -> PyResult<()> {
        info!("Loading sim config...");

        // Parse sim config JSON
        {
            self.sim_config = match serde_json::from_str(&sim_config_json_str) {
                Ok(json) => json,
                Err(_) => Default::default(),
            };
        }

        // Initialize sim clock
        {
            let step_size = Duration::from_millis(
                self.sim_config["clock"]["step_size_ms"]
                    .as_u64()
                    .expect("Invalid config for 'clock':'step_size_ms'"),
            );
            let pace_1x_scale = self.sim_config["clock"]["pace_1x_scale"]
                .as_bool()
                .unwrap_or(true); // default to true if not able to retrieve from config
            self.simclock = Some(Arc::new(SimClock::new(step_size, pace_1x_scale)));
        }

        // Load runtime
        self.runtime = tokio::runtime::Runtime::new().ok();
        let runtime = self
            .runtime
            .as_ref()
            .expect("Couldn't initialize tokio runtime");

        // Load data manager
        {
            let mut data_manager = DataManager::new();
            data_manager.load(&self.sim_config);
            self.data_manager = Some(Arc::new(data_manager));
        }

        // Load middleware
        self.middleware = MiddlewareRegistry::new().get("kafka");
        let middleware = self
            .middleware
            .as_ref()
            .expect("Couldn't initialize middleware");

        // Set up set of required renderers and subscribe to renderer status topic to
        // wait for acknowledgement of renderer readiness before finishing load command
        let required_renderers: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new()));
        {
            {
                // Extract required renderer IDs from sim config
                let mut required_renderers_lock = required_renderers
                    .lock()
                    .expect("Couldn't get required_renderers lock.");

                if let Some(renderer_config) =
                    self.sim_config.get("renderers").and_then(|v| v.as_array())
                {
                    for renderer in renderer_config {
                        if let Some(instance_id) =
                            renderer.get("renderer_id").and_then(|id| id.as_str())
                        {
                            required_renderers_lock.insert(instance_id.to_string());
                        }
                    }
                } else {
                    warn!("No 'renderers' config found in sim config.");
                }

                info!("Required renderers: {:?}", required_renderers_lock);
            } // unlock required_renderers

            // Subscribe to renderer status topic
            match runtime.block_on(
                middleware.subscribe::<JsonData>("aerosim.renderer.status", {
                    let required_renderers = required_renderers.clone();
                    Box::new(move |data, _metadata| {
                        let Some(msg_json) = data.get_data() else {
                            // If message data is not JSON, skip it
                            return Ok(());
                        };

                        if !msg_json["status"]
                            .as_str()
                            .unwrap_or("")
                            .eq("config_loaded")
                        {
                            return Ok(());
                        }

                        let renderer_id = msg_json["renderer_id"].as_str().unwrap_or("");
                        info!("Renderer '{}' loaded config.", renderer_id);

                        let mut required_renderers_lock = required_renderers
                            .lock()
                            .expect("Couldn't get required_renderers lock.");
                        let _ = required_renderers_lock.remove(renderer_id);

                        Ok(())
                    })
                }),
            ) {
                Ok(_) => {}
                Err(e) => {
                    error!("Could not subscribe to renderer status topic: {:?}", e);
                }
            }
        }

        // Publish orchestrator command to load sim config
        let load_cmd_json = JsonData::new(json!({
            "command": "load_config",
            "parameters": {
                "sim_config": self.sim_config
            },
        }));

        info!("Publishing load_config command...");
        match runtime.block_on(middleware.publish::<JsonData>(
            "aerosim.orchestrator.commands",
            &load_cmd_json,
            Some(TimeStamp::new(0, 0)),
        )) {
            Ok(_) => {}
            Err(e) => warn!("Could not publish `aerosim.orchestrator.commands`: {:?}", e),
        };

        // Wait for required renderers to process load command and notify status as ready
        // before finishing load command
        {
            let start_time = std::time::Instant::now();
            let timeout_renderers_ready = Duration::from_secs(30);
            let mut all_renderers_ready = false;
            let mut retry_num = 0;
            while start_time.elapsed() < timeout_renderers_ready {
                {
                    let required_renderers_lock = required_renderers
                        .lock()
                        .expect("Couldn't get required_renderers lock.");
                    if required_renderers_lock.is_empty() {
                        info!("All required renderers loaded config.");
                        all_renderers_ready = true;
                        break;
                    }
                } // unlock required_renderers

                std::thread::sleep(Duration::from_secs(1));
                retry_num += 1;
                if retry_num % 5 == 0 {
                    {
                        let required_renderers_lock = required_renderers
                            .lock()
                            .expect("Couldn't get required_renderers lock.");
                        info!(
                            "Still waiting for required renderers: {:?}",
                            required_renderers_lock
                        );
                    }

                    info!("Retrying publish of the load_config command and waiting up to {} more seconds...",
                        timeout_renderers_ready.as_secs() - start_time.elapsed().as_secs()
                    );

                    match runtime.block_on(middleware.publish::<JsonData>(
                        "aerosim.orchestrator.commands",
                        &load_cmd_json,
                        Some(TimeStamp::new(0, 0)),
                    )) {
                        Ok(_) => {}
                        Err(e) => {
                            warn!("Could not publish `aerosim.orchestrator.commands`: {:?}", e)
                        }
                    };
                }
            }

            if !all_renderers_ready {
                error!("Timed out waiting for renderers to load config.");
                // TODO Return a failed load and stop the sim from continuing to start up if renderers are not ready
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Timed out waiting for renderers to load config.",
                ));
            }
        }

        Ok(())
    }

    fn start(&mut self) -> PyResult<()> {
        info!("Starting orchestrator.");

        // Take ownership of sim clock, data manager, and middleware
        let sim_config = self.sim_config.clone();
        let simclock = self.simclock.take().expect("Sim clock not initialized.");
        let data_manager = self
            .data_manager
            .take()
            .expect("Data manager not initialized.");
        let middleware = self.middleware.take().expect("Middleware not initialized.");
        let runtime = self.runtime.take().expect("Tokio runtime not initialized");

        // Initialize communication channel between sync topics subscriber and the orchestrator.
        let (tx_msg, rx_msg) = mpsc::channel::<(TimeStamp, String)>();

        // Process sync topic data from sim config
        let mut sync_topic_data: Vec<(String, TimeStamp)> = vec![];
        for sync_topic_dict in sim_config["orchestrator"]["sync_topics"]
            .as_array()
            .unwrap()
        {
            if let Some(topic_str) = sync_topic_dict["topic"].as_str() {
                let interval: TimeStamp = match sync_topic_dict["interval_ms"].as_u64() {
                    Some(interval_ms) => TimeStamp::from_millis(interval_ms),
                    None => TimeStamp::new(0, 0),
                };
                sync_topic_data.push((topic_str.to_string(), interval));
            }
        }

        // Retrieve all topics from sim config.
        let mut all_topics: HashSet<(String, String)> = HashSet::new();

        // Retrieve scene graph topics from sim config.
        let mut scene_graph_topics: Vec<String> = Vec::new();
        if let Some(actors) = sim_config["world"]["actors"].as_array() {
            for actor in actors {
                // state
                if let (Some(topic), Some(msg_type)) = (
                    actor["state"]["topic"].as_str(),
                    actor["state"]["msg_type"].as_str(),
                ) {
                    scene_graph_topics.push(topic.to_string());
                    all_topics.insert((msg_type.to_string(), topic.to_string()));
                }

                // effectors
                if let Some(effectors) = actor["effectors"].as_array() {
                    for effector in effectors {
                        if let (Some(topic), Some(msg_type)) = (
                            effector["state"]["topic"].as_str(),
                            effector["state"]["msg_type"].as_str(),
                        ) {
                            scene_graph_topics.push(topic.to_string());
                            all_topics.insert((msg_type.to_string(), topic.to_string()));
                        }
                    }
                }

                // flight_deck
                if let Some(flight_deck) = actor["flight_deck"].as_array() {
                    for flight_deck_obj in flight_deck {
                        if let (Some(topic), Some(msg_type)) = (
                            flight_deck_obj["state"]["topic"].as_str(),
                            flight_deck_obj["state"]["msg_type"].as_str(),
                        ) {
                            scene_graph_topics.push(topic.to_string());
                            all_topics.insert((msg_type.to_string(), topic.to_string()));
                        }
                    }
                }

                // trajectory_visualization
                if actor.get("trajectory_visualization").is_some() {
                    if let (Some(topic), Some(msg_type)) = (
                        actor["trajectory_visualization"]
                            .get("topic")
                            .and_then(|t| t.as_str()),
                        actor["trajectory_visualization"]
                            .get("msg_type")
                            .and_then(|t| t.as_str()),
                    ) {
                        scene_graph_topics.push(topic.to_string());
                        all_topics.insert((msg_type.to_string(), topic.to_string()));
                    }
                }
            }
        }

        // Retrieve fmu topics from sim config.
        if let Some(models) = sim_config["fmu_models"].as_array() {
            for model in models {
                // component_input_topics
                if let Some(input_topics) = model["component_input_topics"].as_array() {
                    for topic in input_topics {
                        if let (Some(topic_name), Some(msg_type)) =
                            (topic["topic"].as_str(), topic["msg_type"].as_str())
                        {
                            all_topics.insert((msg_type.to_string(), topic_name.to_string()));
                        }
                    }
                }

                // component_output_topics
                if let Some(output_topics) = model["component_output_topics"].as_array() {
                    for topic in output_topics {
                        if let (Some(topic_name), Some(msg_type)) =
                            (topic["topic"].as_str(), topic["msg_type"].as_str())
                        {
                            all_topics.insert((msg_type.to_string(), topic_name.to_string()));
                        }
                    }
                }

                // fmu_aux_input_mapping
                if let Some(aux_input) = model["fmu_aux_input_mapping"].as_object() {
                    for (key, value) in aux_input {
                        if value.is_object() {
                            all_topics
                                .insert(("aerosim::types::JsonData".to_string(), key.to_string()));
                        }
                    }
                }

                // fmu_aux_output_mapping
                if let Some(aux_output) = model["fmu_aux_output_mapping"].as_object() {
                    for (key, value) in aux_output {
                        if value.is_object() {
                            all_topics
                                .insert(("aerosim::types::JsonData".to_string(), key.to_string()));
                        }
                    }
                }
            }
        }

        // Subscribe to all topics to be ready to receive sync topics before
        let all_topic_to_subscribe: Vec<(String, String)> = all_topics.into_iter().collect();
        match runtime.block_on(middleware.subscribe_all_raw(all_topic_to_subscribe, {
            // Prepare necessary components to be moved into the callback scope.
            let simclock = Arc::clone(&simclock);
            let data_manager = Arc::clone(&data_manager);
            let scene_graph_data_queue = Arc::clone(&self.scene_graph_data_queue);
            let transport = Arc::clone(&middleware);
            let serializer = transport.get_serializer();

            Box::new(move |payload: &[u8]| {
                // Deserialize metadata from the incoming payload and determine the simulation timestamp.
                // If the simulation timestamp is not valid, compute it based on the real-time platform timestamp.
                let metadata = serializer
                    .deserialize_metadata(payload)
                    .ok_or(format!("Could not deserialize metadata from payload"))?;
                let timestamp = match metadata.is_sim_time_valid() {
                    true => metadata.timestamp_sim,
                    false => simclock.get_sim_time_from_real_time(metadata.timestamp_platform),
                };

                // Process data manager
                data_manager.process_data_message(&metadata, payload, &timestamp);

                // Check if the received payload is related to the scene graph.
                // If it is, deserialize it into the appropriate data type and enqueue it for further processing.
                match scene_graph_topics.contains(&metadata.topic) {
                    true => {
                        match SceneGraphStateData::deserialize(
                            &serializer,
                            &metadata.type_name,
                            payload,
                        ) {
                            Some(state) => match scene_graph_data_queue.lock() {
                                Ok(mut lock) => {
                                    lock.push((timestamp.clone(), metadata.topic.clone(), state))
                                }
                                Err(_) => warn!("Could not enqueue state data for scene graph"),
                            },
                            None => warn!(
                                "Could not deserialize payload into a scene graph actor state"
                            ),
                        }
                    }
                    false => {}
                }

                // Send all received topics to the channel so the orchestrator's main thread
                // can monitor incoming data and iterate accordingly.
                let _ = tx_msg.send((timestamp, metadata.topic));

                Ok(())
            })
        })) {
            Ok(_) => {}
            Err(e) => {
                warn!("Could not subscribe to sync topics: {:?}", e);
            }
        };

        // Start orchestrator thread
        let (tx_stop, rx_stop): (Sender<bool>, Receiver<bool>) = mpsc::channel();
        self.orchestrator_thread_tx_stop = Some(tx_stop);

        let scene_graph_data_queue = Arc::clone(&self.scene_graph_data_queue);
        self.orchestrator_thread_handle = Some(thread::spawn(move || {
            // Main orchestrator thread loop
            runtime.block_on(Orchestrator::orchestrator_main(
                rx_stop,
                rx_msg,
                sim_config,
                sync_topic_data,
                simclock,
                data_manager,
                middleware,
                scene_graph_data_queue,
            ));
        }));

        Ok(())
    }

    fn stop(&mut self) {
        info!("Stopping orchestrator.");
        // Stop orchestrator thread
        match self.orchestrator_thread_tx_stop.take() {
            Some(tx_stop) => match tx_stop.send(true) {
                Ok(_) => {}
                Err(e) => {
                    warn!("Could not send stop flag to orchestrator thread: {:?}", e);
                }
            },
            None => {
                return;
            }
        }

        let handle = self
            .orchestrator_thread_handle
            .take()
            .expect("No clock thread handle, was it started?");

        handle
            .join()
            .expect("Thread should have stopped after receiving stop flag.");
    }
}

// Rust-only Orchestrator methods
impl Orchestrator {
    async fn orchestrator_main(
        rx_stop: Receiver<bool>,
        rx_msg: Receiver<(TimeStamp, String)>,
        sim_config: serde_json::Value,
        sync_topic_data: Vec<(String, TimeStamp)>,
        simclock: Arc<SimClock>,
        data_manager: Arc<DataManager>,
        middleware: Arc<MiddlewareEnum>,
        scene_graph_data_queue: Arc<Mutex<Vec<(TimeStamp, String, SceneGraphStateData)>>>,
    ) {
        info!("Orchestrator main thread started.");
        let mut sim_time = simclock.sim_time().unwrap_or(TimeStamp::new(0, 0));
        let mut running = true;

        let required_renderers: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new()));
        let mut scene_graph = SceneGraph::new();

        // Set up set of required renderers and subscribe to renderer status topic to
        if let Some(renderer_config) = sim_config.get("renderers").and_then(|v| v.as_array()) {
            {
                let mut required_renderers_lock = required_renderers
                    .lock()
                    .expect("Couldn't get required_renderers lock.");
                for renderer in renderer_config {
                    if let Some(instance_id) =
                        renderer.get("renderer_id").and_then(|id| id.as_str())
                    {
                        required_renderers_lock.insert(instance_id.to_string());
                    }
                    info!("Required renderers: {:?}", required_renderers_lock);
                }
            }
        } else {
            warn!("No 'renderers' config found in sim config.");
        }

        match middleware
            .subscribe::<JsonData>("aerosim.renderer.status", {
                let required_renderers = required_renderers.clone();
                Box::new(move |data, _metadata| {
                    let Some(msg_json) = data.get_data() else {
                        // If message data is not JSON, skip it
                        return Ok(());
                    };

                    if !msg_json["status"]
                        .as_str()
                        .unwrap_or("")
                        .eq("scene_graph_loaded")
                    {
                        return Ok(());
                    }

                    let renderer_id = msg_json["renderer_id"].as_str().unwrap_or("");
                    info!("Renderer '{}' loaded scene graph.", renderer_id);

                    let mut required_renderers_lock = required_renderers
                        .lock()
                        .expect("Couldn't get required_renderers lock.");
                    let _ = required_renderers_lock.remove(renderer_id);

                    Ok(())
                })
            })
            .await
        {
            Ok(_) => {}
            Err(e) => {
                error!("Could not subscribe to renderer status topic: {:?}", e);
            }
        }

        // Load world from sim config
        scene_graph.load_world(&sim_config["world"], &sim_config["renderers"]);
        let load_scene_graph_json = scene_graph.generate_scene_graph_json();

        // Publish orchestrator command to load sim config
        let load_cmd_json = JsonData::new(json!({
            "command": "load_scene_graph",
            "parameters": {
                "scene_graph": load_scene_graph_json
            },
        }));

        info!("Publishing load_scene_graph command.");
        match middleware
            .publish::<JsonData>(
                "aerosim.orchestrator.commands",
                &load_cmd_json,
                Some(TimeStamp::new(0, 0)),
            )
            .await
        {
            Ok(_) => {}
            Err(e) => warn!("Could not publish `aerosim.orchestrator.commands`: {:?}", e),
        };

        // Wait for required renderers to process load scene graph command and notify
        // status as ready before publishing the sim start command
        {
            let start_time = std::time::Instant::now();
            let timeout_renderers_ready = Duration::from_secs(30);
            let mut all_renderers_ready = false;
            let mut retry_num = 0;
            while start_time.elapsed() < timeout_renderers_ready {
                {
                    let required_renderers_lock = required_renderers
                        .lock()
                        .expect("Couldn't get required_renderers lock.");
                    if required_renderers_lock.is_empty() {
                        info!("All required renderers loaded.");
                        all_renderers_ready = true;
                        break;
                    }
                } // unlock required_renderers

                tokio::time::sleep(Duration::from_millis(100)).await;
                retry_num += 1;
                if retry_num % 50 == 0 {
                    let required_renderers_lock = required_renderers
                        .lock()
                        .expect("Couldn't get required_renderers lock.");
                    info!(
                        "Still waiting up to {} more seconds for required renderers: {:?}",
                        timeout_renderers_ready.as_secs() - start_time.elapsed().as_secs(),
                        required_renderers_lock
                    );
                }
            }

            if !all_renderers_ready {
                error!("Timed out waiting for renderers to load scene graph.");
                running = false;
            }
        }

        // Start sim clock and publish orchestrator start command
        if running {
            let sim_start_time = simclock.start();
            let start_cmd_json = JsonData::new(json!({
                "command": "start",
                "parameters": {
                    "sim_start_time": {
                        "sec": sim_start_time.sec,
                        "nanosec": sim_start_time.nanosec
                    }
                },
            }));

            match middleware
                .publish::<JsonData>(
                    "aerosim.orchestrator.commands",
                    &start_cmd_json,
                    Some(TimeStamp::new(0, 0)),
                )
                .await
            {
                Ok(_) => {}
                Err(e) => warn!("Could not publish `aerosim.orchestrator.commands`: {:?}", e),
            }

            info!("Published sim start command.");
        }

        // Wait to receive an initial published message from each of sync_topics as
        // a response from the start command before starting the main loop to tick
        // the sim clock.
        {
            let start_time = std::time::Instant::now();
            let timeout_initial_sync_topics = Duration::from_secs(60);
            let mut sync_topics_set =
                Orchestrator::get_sync_topics_for_simtime(&sync_topic_data, sim_time);
            let mut notify_at_sec = 5;
            info!(
                "Waiting to receive initial sync topics: {:?}",
                sync_topics_set
            );

            while running {
                running = Orchestrator::poll_messages(&mut sync_topics_set, &rx_msg, &rx_stop);

                if sync_topics_set.is_empty() {
                    break;
                }

                if start_time.elapsed() > timeout_initial_sync_topics {
                    warn!("Timed out waiting for initial sync topics.");
                    running = false;
                } else if start_time.elapsed().as_secs() == notify_at_sec {
                    info!(
                        "Still waiting up to {} more seconds for initial sync topics: {:?}",
                        timeout_initial_sync_topics.as_secs() - start_time.elapsed().as_secs(),
                        sync_topics_set
                    );
                    notify_at_sec += 5;
                }

                match rx_stop.try_recv() {
                    Ok(flag) => {
                        if flag {
                            running = false;
                        }
                    }
                    Err(TryRecvError::Disconnected) => {
                        running = false;
                    }
                    Err(TryRecvError::Empty) => { /* pass to continue looping */ }
                }
            }

            info!("Done polling for initial sync topic messages.");
        }

        // Start main loop
        while running {
            // info!("Orchestrator thread tick.");
            let actual_time_start = tokio::time::Instant::now();

            // Step sim clock
            sim_time = simclock.step();

            // Publish sim clock time step
            {
                let now_platform = TimeStamp::now();
                let sim_time_json = JsonData::new(json!({
                    "timestamp_sim": {
                        "sec": sim_time.sec,
                        "nanosec": sim_time.nanosec
                    },
                    "timestamp_platform": {
                        "sec": now_platform.sec,
                        "nanosec": now_platform.nanosec
                    },
                    "tick_group": 1  // TODO implement tick groups
                }));
                match middleware
                    .publish::<JsonData>("aerosim.clock", &sim_time_json, Some(sim_time))
                    .await
                {
                    Ok(_) => {}
                    Err(e) => warn!("Could not pusblish `aerosim.clock`: {:?}", e),
                };

                debug!(
                    "=== Published sim clock time step: {} sec, {} nanosec ===",
                    sim_time.sec, sim_time.nanosec
                );
            }

            // Wait to receive a published message from each of sync_topics before advancing.
            {
                let mut sync_topics_set =
                    Orchestrator::get_sync_topics_for_simtime(&sync_topic_data, sim_time);
                // debug!("Waiting to receive sync topics: {:?}", sync_topics_set);
                while running {
                    running = Orchestrator::poll_messages(&mut sync_topics_set, &rx_msg, &rx_stop);

                    if sync_topics_set.is_empty() {
                        break;
                    }
                }
                // debug!("Received all sync topic messages.");
            }

            // Update scene graph
            let data_queue = match scene_graph_data_queue.lock() {
                Ok(mut lock) => std::mem::take(&mut *lock),
                Err(_) => {
                    warn!("Failed to acquire lock for scene graph data queue. Using empty queue as fallback.");
                    Vec::new()
                }
            };
            match scene_graph.update_world(data_queue, &sim_time) {
                Some(scene_graph_update_json) => {
                    let data = JsonData::new(scene_graph_update_json);
                    match middleware
                        .publish::<JsonData>("aerosim.scene_graph.update", &data, Some(sim_time))
                        .await
                    {
                        Ok(_) => {}
                        Err(e) => warn!("Could not publish `aerosim.scene_graph.update`: {:?}", e),
                    };
                }
                None => {}
            };

            // Handle time step pacing if enabled
            let actual_time_elapsed = actual_time_start.elapsed();
            if actual_time_elapsed > simclock.step_size {
                warn_rate_limited(
                    "tick_time_exceeded",
                    &format!(
                        "Actual tick time elapsed={} ms exceeds clock step size={} ms",
                        actual_time_elapsed.as_millis(),
                        simclock.step_size.as_millis()
                    ),
                    Duration::from_secs(1),
                );
            } else if simclock.pace_1x_scale && actual_time_elapsed < simclock.step_size {
                // Sleep for the remaining actual step time duration
                let time_to_sleep = simclock.step_size - actual_time_elapsed;
                // info!(
                //     "Sleeping for {} ms",
                //     time_to_sleep.as_millis()
                // );
                let wait_time = std::time::SystemTime::now();
                while wait_time.elapsed().unwrap() < time_to_sleep {
                    tokio::time::sleep(Duration::ZERO).await; // on Windows, sleep() for >0 is not accurate
                }
            }
        } // end of main running loop

        // Orchestrator main thread is stopping
        let sim_stop_time = simclock.stop();

        // Publish orchestrator command to stop sim
        let stop_cmd_json = JsonData::new(json!({
            "command": "stop",
            "parameters": {},
        }));
        match middleware
            .publish::<JsonData>(
                "aerosim.orchestrator.commands",
                &stop_cmd_json,
                Some(sim_stop_time),
            )
            .await
        {
            Ok(_) => {}
            Err(e) => warn!(
                "Could not pusblish `aerosim.orchestrator.commands`: {:?}",
                e
            ),
        };

        // Stop data manager
        data_manager.stop();

        info!("Orchestrator thread stopped.");
    }

    fn get_sync_topics_for_simtime(
        sync_topic_data: &Vec<(String, TimeStamp)>,
        sim_time: TimeStamp,
    ) -> HashSet<String> {
        let mut topics_to_sync: HashSet<String> = HashSet::new();
        for (topic, interval) in sync_topic_data {
            let mut sec_match = true;
            let mut nanosec_match = true;
            if interval.sec > 0 {
                sec_match = sim_time.sec % interval.sec == 0;
            }
            if interval.nanosec > 0 {
                nanosec_match = sim_time.nanosec % interval.nanosec == 0;
            }
            if sec_match && nanosec_match {
                topics_to_sync.insert(topic.clone());
            }
        }
        topics_to_sync
    }

    fn poll_messages(
        sync_topics: &mut HashSet<String>,
        rx_msg: &Receiver<(TimeStamp, String)>,
        rx_stop: &Receiver<bool>,
    ) -> bool {
        let mut keep_running = true;

        if sync_topics.is_empty() {
            return keep_running;
        }

        match rx_msg.try_recv() {
            Ok(msg) => {
                let _timestamp = msg.0;
                let topic = msg.1;

                // Process sync topics
                let _was_removed = sync_topics.remove(&topic);
            }
            Err(TryRecvError::Disconnected) => {
                keep_running = false;
            }
            Err(TryRecvError::Empty) => { /* pass to continue looping */ }
        }

        match rx_stop.try_recv() {
            Ok(flag) => {
                if flag {
                    keep_running = false;
                }
            }
            Err(TryRecvError::Disconnected) => {
                keep_running = false;
            }
            Err(TryRecvError::Empty) => { /* pass to continue looping */ }
        }

        keep_running
    }
}
