use std::collections::HashSet;
use std::sync::{Arc, Mutex};
use std::thread;
use std::vec;
use std::{cmp::Ordering, collections::BinaryHeap};

use log::{info, warn};
use serde::Deserialize;
use serde_json::json;
use tokio::sync::mpsc::error::TryRecvError;
use uuid::Uuid;

use aerosim_data::{
    middleware::{
        BincodeSerializer, Metadata, Middleware, MiddlewareEnum, MiddlewareRaw, MiddlewareRegistry,
        Serializer,
    },
    types::{CompressedImage, Image, JsonData, TimeStamp},
    AerosimMessage,
};

#[derive(Deserialize)]
struct RendererConfig {
    #[serde(rename = "renderer_id")]
    instance_id: String,
    role: String,
    sensors: Vec<String>,
}

// -------------------------------------------------------------------------
// Payload and PayloadQueue

#[derive(Default, Clone, PartialEq)]
pub struct Payload {
    pub timestamp: f64,
    pub raw_payload: String,
}

impl Eq for Payload {}

impl PartialOrd for Payload {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        // Reverse ordering for smallest timestamp first
        other.timestamp.partial_cmp(&self.timestamp)
    }
}

impl Ord for Payload {
    fn cmp(&self, other: &Payload) -> Ordering {
        self.partial_cmp(other).unwrap()
    }
}

#[derive(Default)]
pub struct PayloadQueue {
    pub queue: BinaryHeap<Payload>,
    pub oldest_timestamp: Option<f64>,
    pub newest_timestamp: Option<f64>,
}

impl PayloadQueue {
    pub fn new() -> Self {
        PayloadQueue {
            queue: BinaryHeap::new(),
            oldest_timestamp: None,
            newest_timestamp: None,
        }
    }

    pub fn push(&mut self, payload: Payload) {
        match self.oldest_timestamp {
            Some(oldest_timestamp) => {
                if payload.timestamp < oldest_timestamp {
                    self.oldest_timestamp = Some(payload.timestamp);
                }
            }
            None => {
                self.oldest_timestamp = Some(payload.timestamp);
            }
        }

        match self.newest_timestamp {
            Some(newest_timestamp) => {
                if payload.timestamp > newest_timestamp {
                    self.newest_timestamp = Some(payload.timestamp);
                }
            }
            None => {
                self.newest_timestamp = Some(payload.timestamp);
            }
        }

        self.queue.push(payload);
    }
}

// -------------------------------------------------------------------------
// MessageHandler

// #[derive(Default)]
pub struct MessageHandler {
    renderer_id: String, // Instance ID set by the renderer that creates the MessageHandler
    _sim_config: serde_json::Value,
    runtime: Arc<tokio::runtime::Runtime>,
    transport: Arc<MiddlewareEnum>,
    payload_queue: Arc<Mutex<PayloadQueue>>,
    assigned_sensors: Arc<Mutex<HashSet<String>>>,

    // Handle for the thread running the async message publishing pipeline
    // Used to manage the lifecycle of the thread
    thread_handle: Option<thread::JoinHandle<()>>,

    // Channel used to signal the thread to stop execution
    tx_stop: Arc<tokio::sync::mpsc::Sender<bool>>,
    rx_stop: Option<tokio::sync::mpsc::Receiver<bool>>,

    // Channel for sending images through an asynchronous processing pipeline
    tx_img: Arc<tokio::sync::mpsc::Sender<(String, Image)>>,
    rx_img: Option<tokio::sync::mpsc::Receiver<(String, Image)>>,
}

impl MessageHandler {
    pub fn new(renderer_id: &str) -> Self {
        info!("[aerosim.renderer.message_handler] Creating a new MessageHandler.");

        let (tx_stop, rx_stop) = tokio::sync::mpsc::channel::<bool>(1);
        let (tx_img, rx_img) = tokio::sync::mpsc::channel::<(String, Image)>(1);

        MessageHandler {
            renderer_id: renderer_id.to_string(),
            _sim_config: serde_json::Value::Null,
            runtime: Arc::new(tokio::runtime::Runtime::new().unwrap()),
            transport: MiddlewareRegistry::new().get("kafka").unwrap(),
            payload_queue: Arc::new(Mutex::new(PayloadQueue::new())),
            assigned_sensors: Arc::new(Mutex::new(HashSet::new())),
            thread_handle: None,
            tx_stop: Arc::new(tx_stop),
            rx_stop: Some(rx_stop),
            tx_img: Arc::new(tx_img),
            rx_img: Some(rx_img),
        }
    }

    pub fn start(&mut self) -> Result<(), ()> {
        info!("[aerosim.renderer.message_handler] Starting message handler.");

        let runtime = Arc::clone(&self.runtime);
        let transport = Arc::clone(&self.transport);
        let payload_queue = Arc::clone(&self.payload_queue);
        let assigned_sensors = Arc::clone(&self.assigned_sensors);
        let instance_id = self.renderer_id.clone();
        let rx_img = self.rx_img.take().unwrap();
        let rx_stop = self.rx_stop.take().unwrap();
        self.thread_handle = Some(thread::spawn(move || {
            runtime.block_on(message_handler_main(
                transport,
                payload_queue,
                assigned_sensors,
                instance_id,
                rx_img,
                rx_stop,
            ));
        }));

        info!("[aerosim.renderer.message_handler] Message handler started.");
        Ok(())
    }

    pub fn notify_scene_graph_loaded(&self) {
        info!("[aerosim.renderer.message_handler] Notifying that the scene graph has been loaded.");
        let payload = json!({
            "renderer_id": format!("{}", self.renderer_id).as_str(),
            "status": "scene_graph_loaded",
        });
        let payload_jsondata = JsonData::new(payload);
        futures::executor::block_on(self.transport.publish(
            "aerosim.renderer.status",
            &payload_jsondata,
            None,
        ))
        .ok();
    }

    pub fn stop(&mut self) -> Result<(), ()> {
        info!("[aerosim.renderer.message_handler] Stopping message handler.");

        self.tx_stop.blocking_send(true);
        let handle = self
            .thread_handle
            .take()
            .expect("No message thread handle, was it started?");

        handle
            .join()
            .expect("Thread should have stopped after receiving stop flag.");

        self.transport.shutdown();

        info!("[aerosim.renderer.message_handler] Message handler stopped.");
        Ok(())
    }

    pub fn publish_to_topic(&self, topic: &str, payload: &str) {
        let payload_json = serde_json::from_str::<serde_json::Value>(payload)
            .expect("Error serializing payload string to JSON.");
        let payload_jsondata = JsonData::new(payload_json);
        futures::executor::block_on(self.transport.publish(topic, &payload_jsondata, None)).ok();
    }

    pub fn publish_image_to_topic(&self, topic: &str, image: Image) {
        let _ = self.tx_img.try_send((topic.to_string(), image));
    }

    pub fn get_payload_queue_size(&self) -> u32 {
        let q_size = self.payload_queue.lock().unwrap().queue.len();
        q_size as u32
    }

    pub fn get_payload_queue_oldest_timestamp(&self) -> f64 {
        let oldest_timestamp = self.payload_queue.lock().unwrap().oldest_timestamp;
        oldest_timestamp.unwrap_or(-1.0)
    }

    pub fn get_payload_queue_newest_timestamp(&self) -> f64 {
        let oldest_timestamp = self.payload_queue.lock().unwrap().newest_timestamp;
        oldest_timestamp.unwrap_or(-1.0)
    }

    pub fn get_payload_from_queue(&self) -> Option<String> {
        let payload_q = &mut self.payload_queue.lock().unwrap();
        if payload_q.queue.len() > 0 {
            // Get the oldest payload from the queue
            let payload = payload_q.queue.pop().unwrap().raw_payload;

            // If there are still more payloads in the queue, update the oldest timestamp,
            // otherwise clear the oldest and newest timestamps
            if payload_q.queue.len() > 0 {
                let next_timestamp = payload_q.queue.peek().unwrap().timestamp;
                payload_q.oldest_timestamp = Some(next_timestamp);
            } else {
                payload_q.oldest_timestamp = None;
                payload_q.newest_timestamp = None;
            }

            return Some(payload);
        }
        None
    }
}

// -------------------------------------------------------------------------
// Message Handler main function run from start()

async fn message_handler_main(
    transport: Arc<MiddlewareEnum>,
    payload_queue: Arc<Mutex<PayloadQueue>>,
    assigned_sensors: Arc<Mutex<HashSet<String>>>,
    renderer_id: String,
    mut rx_img: tokio::sync::mpsc::Receiver<(String, Image)>,
    mut rx_stop: tokio::sync::mpsc::Receiver<bool>,
) {
    {
        match transport
            .subscribe::<JsonData>("aerosim.orchestrator.commands", {
                let transport = Arc::clone(&transport);
                let payload_queue = Arc::clone(&payload_queue);
                let assigned_sensors = Arc::clone(&assigned_sensors);
                let instance_id = renderer_id.clone();
                Box::new(move |data, metadata| {
                    handle_orchestrator_command_message(
                        &data,
                        &metadata,
                        &instance_id,
                        &assigned_sensors,
                        &payload_queue,
                        &transport,
                    );
                    Ok(())
                })
            })
            .await
        {
            Ok(()) => {
                println!("[aerosim.world.link] Created aerosim.orchestrator.commands subscriber.")
            }
            Err(_) => eprintln!(
                "[aerosim.world.link] Could not create aerosim.orchestrator.commands subscriber."
            ),
        }

        match transport
            .subscribe::<JsonData>("aerosim.scene_graph.update", {
                let payload_queue = Arc::clone(&payload_queue);
                let assigned_sensors = Arc::clone(&assigned_sensors);
                let instance_id = renderer_id.clone();
                Box::new(move |data, metadata| {
                    // Process scene graph update message
                    handle_scene_graph_update_message(
                        &data,
                        &metadata,
                        &assigned_sensors,
                        &instance_id,
                        &payload_queue,
                    );
                    Ok(())
                })
            })
            .await
        {
            Ok(()) => {
                println!("[aerosim.world.link] Created aerosim.scene_graph.update subscriber.")
            }
            Err(_) => eprintln!(
                "[aerosim.world.link] Could not create aerosim.scene_graph.update subscriber."
            ),
        }
    }

    // Process image publishing asynchronously in this loop.
    // This helps avoid blocking the renderer while the middleware is publishing the image.
    // The channel buffer between the renderer thread and this thread is set to 1.
    // If the buffer already contains an image and the renderer tries to add a new one,
    // the new image will be discarded (i.e., image loss is possible).
    loop {
        match rx_img.try_recv() {
            Ok((topic, image)) => {
                // TODO: Properly pass `timestamp_sim` and `timestamp_platform` from the renderer. 
                let metadata = Metadata::new(&topic, &CompressedImage::get_type_name(), None, None);
                let compressed_image = match image.compress() {
                    Ok(compressed_image) => {
                        // The Kafka middleware defaults to a JSON serializer. A Bincode serializer is used
                        // here to improve encoding and decoding performance, handled through the middleware's raw API.
                        let serializer = BincodeSerializer {};
                        match serializer.serialize_message(&metadata, &compressed_image) {
                            Some(payload) => {
                                transport
                                    .publish_raw(
                                        &CompressedImage::get_type_name(),
                                        &topic,
                                        &payload,
                                    )
                                    .await;
                            }
                            None => eprintln!("Could not serialize image using bincode"),
                        }
                    }
                    Err(_) => eprintln!("Could not compress raw image to jpeg"),
                };
            }
            Err(TryRecvError::Empty) => { /* pass to continue looping */ }
            Err(e) => eprintln!("Error receiving image: {:?}", e),
        }

        match rx_stop.try_recv() {
            Ok(stop) => {
                if stop {
                    break;
                }
            }
            Err(_) => {}
        }
    }
}

// Function to extract transform parameters from JSON and send to renderer
fn handle_orchestrator_command_message(
    payload: &JsonData,
    metadata: &Metadata,
    instance_id: &str,
    assigned_sensors: &Arc<Mutex<HashSet<String>>>,
    payload_queue: &Arc<Mutex<PayloadQueue>>,
    transport: &Arc<MiddlewareEnum>,
) {
    // Parse JSON message from the payload
    let Some(msg_data) = payload.get_data() else {
        println!("Failed to parse message JSON: {:?}", payload);
        return;
    };

    let command_str = msg_data["command"]
        .as_str()
        .expect("Error parsing 'command' data");

    println!(
        "[aerosim.world.link] Received orchestrator command: {}",
        command_str
    );

    if command_str == "load_config" {
        // --------------------------------------------------------------
        // Process orchestrator load config command
        // --------------------------------------------------------------

        // Check 'renderers' config for this renderer's instance ID
        let sim_config = &msg_data["parameters"]["sim_config"];

        if let Some(renderer_configs_json) = sim_config.get("renderers") {
            let renderer_configs: Vec<RendererConfig> =
                match serde_json::from_value(renderer_configs_json.clone()) {
                    Ok(renderer_configs) => renderer_configs,
                    Err(e) => {
                        warn!(
                            "[aerosim.world.link] Failed to parse renderer configurations: {:?}",
                            e
                        );
                        vec![]
                    }
                };

            for renderer_config in renderer_configs {
                if renderer_config.instance_id == instance_id {
                    info!(
                        "[aerosim.world.link] Renderer configurations found for renderer ID: {}",
                        instance_id
                    );
                    let mut assigned_sensors_lock = assigned_sensors
                        .lock()
                        .expect("Failed to lock assigned_sensors");
                    *assigned_sensors_lock = HashSet::from_iter(renderer_config.sensors);
                    if assigned_sensors_lock.is_empty() {
                        info!("[aerosim.world.link] No sensors assigned to renderer.");
                    } else {
                        info!(
                            "[aerosim.world.link] Assigned sensors: {:?}",
                            assigned_sensors_lock
                        );
                    }
                }
            }

            info!(
                "[aerosim.world.link] Broadcasting availability of renderer with Instance ID: {}.",
                instance_id
            );
            let announcement = json!({
                "renderer_id": format!("{}", instance_id).as_str(),
                "status": "config_loaded",
            });
            let payload = JsonData::new(announcement);

            futures::executor::block_on(transport.publish(
                "aerosim.renderer.status",
                &payload,
                Some(metadata.timestamp_sim),
            ))
            .ok();
        } else {
            warn!("[aerosim.world.link] Failed to find renderer configurations in message.");

            info!(
                "[aerosim.world.link] Broadcasting availability of renderer with Instance ID: {}.",
                instance_id
            );
            let announcement = json!({
                "renderer_id": format!("{}", instance_id).as_str(),
                "status": "config_error",
            });
            let payload = JsonData::new(announcement);

            futures::executor::block_on(transport.publish(
                "aerosim.renderer.status",
                &payload,
                Some(metadata.timestamp_sim),
            ))
            .ok();
        }
    } else if command_str == "load_scene_graph" {
        info!(
            "[aerosim.world.link] Processing load_scene_graph command for renderer with Instance ID: {}.",
            instance_id
        );

        let scene_graph = &msg_data["parameters"]["scene_graph"];

        // TODO: Filter out data for non-assigned sensors
        let assigned_sensors_vec = assigned_sensors
            .lock()
            .expect("Failed to lock assigned_sensors")
            .iter()
            .cloned()
            .collect::<Vec<String>>();
        let filtered_scene_graph =
            filter_scene_graph_data(&scene_graph, assigned_sensors_vec, instance_id);

        // Set payload timestamp as the message's platform timestamp since it
        // is used for real-time pacing of the renderer.
        let payload_timestamp: f64 = metadata.timestamp_platform.sec as f64
            + metadata.timestamp_platform.nanosec as f64 / 1_000_000_000.0;

        let mut payload_queue_lock = payload_queue.lock().unwrap();
        payload_queue_lock.push(Payload {
            timestamp: payload_timestamp,
            raw_payload: serde_json::to_string(&filtered_scene_graph)
                .expect("Error serializing sene_graph message to JSON."),
        });
    }
}

fn filter_scene_graph_data(
    scene_graph: &serde_json::Value,
    assigned_sensors: Vec<String>,
    instance_id: &str,
) -> serde_json::Value {
    let mut filtered_scene_graph = scene_graph.clone();

    // Filter viewport_configs in resources: pick a single matching viewport_config.
    // If no matching config exists, remove the viewport configuration key.
    if let Some(resources) = filtered_scene_graph.get_mut("resources") {
        if let Some(viewport_configs) = resources.get_mut("viewport_configs") {
            if let Some(vp_array) = viewport_configs.as_array_mut() {
                // Retain only viewport configs for the provided instance_id.
                let matching_configs: Vec<serde_json::Value> = vp_array
                    .iter()
                    .filter(|vp| {
                        vp.get("renderer_instance")
                            .and_then(|v| v.as_str())
                            .map(|id| id == instance_id)
                            .unwrap_or(false)
                    })
                    .cloned()
                    .collect();

                // If a matching config exists, replace the array with a single object.
                if let Some(selected_config) = matching_configs.into_iter().next() {
                    if let Some(resources_obj) = resources.as_object_mut() {
                        resources_obj.remove("viewport_configs");
                        resources_obj.insert("viewport_config".to_string(), selected_config);
                    }
                } else if let Some(resources_obj) = resources.as_object_mut() {
                    // No matching viewport configuration exists: remove the key entirely.
                    resources_obj.remove("viewport_configs");
                }
            }
        }
    }

    // TODO: Filter out entities based on assigned sensors.

    filtered_scene_graph
}

fn handle_scene_graph_update_message(
    payload: &JsonData,
    metadata: &Metadata,
    assigned_sensors: &Arc<Mutex<HashSet<String>>>,
    instance_id: &str,
    payload_queue: &Arc<Mutex<PayloadQueue>>,
) {
    // Parse JSON message from the payload
    let Some(msg_data) = payload.get_data() else {
        println!("Failed to parse message JSON: {:?}", payload);
        return;
    };

    // --------------------------------------------------------------
    // TODO: Filter out data for non-assigned sensors
    // --------------------------------------------------------------
    let assigned_sensors_vec = assigned_sensors
        .lock()
        .expect("Failed to lock assigned_sensors")
        .iter()
        .cloned()
        .collect::<Vec<String>>();

    let filtered_scene_graph =
        filter_scene_graph_data(&msg_data, assigned_sensors_vec, instance_id);
    {
        // Set payload timestamp as the message's platform timestamp since it
        // is used for real-time pacing of the renderer.
        let payload_timestamp: f64 = metadata.timestamp_platform.sec as f64
            + metadata.timestamp_platform.nanosec as f64 / 1_000_000_000.0;

        let mut payload_queue_lock = payload_queue.lock().unwrap();
        payload_queue_lock.push(Payload {
            timestamp: payload_timestamp,
            raw_payload: serde_json::to_string(&filtered_scene_graph)
                .expect("Error serializing renderer message to JSON."),
        });
    } // unlock payload_queue
}
