use tokio;

use std::error::Error;
use std::time::Duration;

use aerosim_data::middleware::{Metadata, Middleware, MiddlewareRaw, MiddlewareRegistry, Serializer};
use aerosim_data::types::{JsonData, Vector3};

async fn subscribe_to_vector3(registry: &MiddlewareRegistry) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("kafka").unwrap();
    middleware.subscribe(
        "vector3",
        Box::new(|stamp: Vector3, _metadata: Metadata| { println!("Received vector: {:?}", stamp); Ok(()) })
    ).await
}

async fn subscribe_to_json(registry: &MiddlewareRegistry) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("kafka").unwrap();
    middleware.subscribe(
        "json",
        Box::new(|json: JsonData, _metadata: Metadata| {
            let json = json.get_data().unwrap();
            println!("Received json data: {:?}", json);
            Ok(())
        })
    ).await
}

async fn subscribe_raw(registry: &MiddlewareRegistry) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("kafka").unwrap();
    let serializer = middleware.get_serializer();
    middleware.subscribe_all_raw(
        vec![("aerosim::types::JsonData".to_string(), "json".to_string()), ("aerosim::types::Vector3".to_string(), "vector3".to_string())],
        Box::new(move |payload: &[u8]| {
            let metadata: Metadata = serializer.deserialize_metadata(payload).unwrap();
            match metadata.type_name.as_str() {
                "aerosim::types::JsonData" => println!("Received raw json data: {:?}", serializer.deserialize_data::<JsonData>(payload)),
                "aerosim::types::Vector3" => println!("Received raw vector: {:?}", serializer.deserialize_data::<Vector3>(payload)),
                _ => println!("Received unknown data message type"),
            };
            Ok(())
        })
    ).await
}

#[tokio::main]
async fn main() {
    let registry = MiddlewareRegistry::new();
    let _ = subscribe_to_vector3(registry).await;
    let _ = subscribe_to_json(registry).await;
    let _ = subscribe_raw(registry).await;

    let mut interval = tokio::time::interval(Duration::from_secs(1));
    loop {
        interval.tick().await;
    };
}
