use ::log::{info, warn};
use std::{
    borrow::Cow,
    collections::HashMap,
    fs::File,
    io::BufWriter,
    sync::{Arc, Mutex},
};

use mcap::{Channel, Message, Schema, Writer};
use serde_json;

use aerosim_data::{
    middleware::Metadata,
    types::{TimeStamp, TypeRegistry},
};

pub struct DataManager {
    enabled: bool,
    /// Ensures thread-safe management of the file's open/closed state.
    is_open: Mutex<bool>,
    writer: Mutex<Option<Writer<BufWriter<File>>>>,
    schemas: Mutex<HashMap<String, Option<Arc<Schema<'static>>>>>,
    channels: Mutex<HashMap<String, Arc<Channel<'static>>>>,
}

impl DataManager {
    pub fn new() -> Self {
        DataManager {
            enabled: false,
            is_open: Mutex::new(false),
            writer: Mutex::new(None),
            schemas: Mutex::new(HashMap::new()),
            channels: Mutex::new(HashMap::new()),
        }
    }

    pub fn load(&mut self, sim_config: &serde_json::Value) {
        info!("Load data manager.");

        // Check if mcap logging is enabled
        self.enabled = sim_config
            .pointer("/orchestrator/output_sim_data_file")
            .is_some();

        match self.enabled {
            true => {
                let filename = sim_config
                    .pointer("/orchestrator/output_sim_data_file")
                    .and_then(|f| f.as_str())
                    .expect("Could not extract MCAP filename from configuration file");

                let file = File::create(filename).expect("Failed to create MCAP file");

                let writer = mcap::WriteOptions::default()
                    .use_chunks(false)
                    .create(BufWriter::new(file))
                    .expect("Could not create MCAP writer");
                {
                    let mut lock = self.writer.lock().unwrap();
                    *lock = Some(writer);
                }

                {
                    match self.is_open.lock() {
                        Ok(mut lock) => *lock = true,
                        Err(_) => return,
                    };
                }
            }
            false => {}
        };
    }

    pub fn process_data_message(&self, metadata: &Metadata, payload: &[u8], timestamp: &TimeStamp) {
        if !self.enabled {
            return;
        }

        match self.is_open.lock() {
            // Prevent writing to the file if it is already closed (e.g., after `stop` has been called).
            Ok(lock) if !*lock => return,
            // If the file is open continue with the writing process.
            Ok(_) => {}
            Err(_) => {
                warn!("Could not lock MCAP writing process");
                return;
            }
        };

        let channel: Arc<Channel<'_>> = {
            let mut channels = self.channels.lock().unwrap();

            if !channels.contains_key(&metadata.topic) {
                info!("Creating MCAP channel for {}", &metadata.topic);

                let schema: Option<Arc<Schema<'_>>> = {
                    let mut schemas = self.schemas.lock().unwrap();

                    if !schemas.contains_key(&metadata.type_name) {
                        let data = TypeRegistry::new()
                            .get(&metadata.type_name)
                            .and_then(|ts| ts.schema_as_bytes());

                        let schema = match data {
                            Some(schema_data) => Some(Arc::new(Schema {
                                id: schemas.len() as u16,
                                name: (&metadata.type_name).to_string(),
                                encoding: "jsonschema".to_string(),
                                data: Cow::Owned(schema_data),
                            })),
                            None => None,
                        };

                        schemas.insert(metadata.type_name.clone(), schema);
                    }

                    match schemas.get(&metadata.type_name).cloned() {
                        Some(schema) => schema,
                        None => None,
                    }
                };

                let _channel = Channel {
                    id: channels.len() as u16,
                    topic: metadata.topic.clone(),
                    message_encoding: "json".to_string(),
                    metadata: Default::default(),
                    schema,
                };
                channels.insert(metadata.topic.clone(), Arc::new(_channel));
            }

            match channels.get(&metadata.topic).cloned() {
                Some(channel) => Some(channel),
                None => None,
            }
        }
        .expect("Could not create MCAP channel");

        let message = Message {
            channel: channel.clone(),
            sequence: 0 as u32,
            log_time: TimeStamp::now().to_nanos(),
            publish_time: timestamp.to_nanos(),
            data: Cow::Borrowed(payload),
        };

        {
            match self.writer.lock() {
                Ok(mut lock) => match lock.as_mut() {
                    Some(writer) => {
                        let _ = writer.write(&message);
                    }
                    None => {
                        warn!("MCAP writer is not initialized")
                    }
                },
                Err(_) => warn!("Could not lock MCAP writer"),
            };
        }
    }

    pub fn stop(&self) {
        {
            if !self.enabled {
                return;
            }

            match self.is_open.lock() {
                // Prevent further messages from being written by marking the file as closed.
                Ok(mut lock) => *lock = false,
                Err(_) => {
                    warn!("Could not lock MCAP writing process");
                    return;
                }
            };

            let mut lock = self.writer.lock().unwrap();
            match lock.as_mut() {
                Some(writer) => {
                    let _ = writer.finish();
                }
                None => warn!("MCAP writer is not initialized"),
            };
        }
    }
}
