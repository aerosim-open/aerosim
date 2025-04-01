use tokio;

use std::error::Error;
use std::time::Duration;

use aerosim_data::middleware::{Metadata, MiddlewareRegistry, Middleware};
use aerosim_data::types::Vector3;

async fn subscribe_to_vector3(registry: &MiddlewareRegistry) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("dds").unwrap();
    middleware.subscribe(
        "vector3",
        Box::new(|data: Vector3, metadata: Metadata| { println!("Received vector ({}): {:?}", metadata.topic, data); Ok(()) })
    ).await
}

#[tokio::main]
async fn main() {
    let registry = MiddlewareRegistry::new();
    let transport = registry.get("dds").unwrap();
    let _ = subscribe_to_vector3(registry).await;

    let mut interval = tokio::time::interval(Duration::from_secs(1));
    for _ in 0..30 {
        interval.tick().await;
    }

    transport.shutdown();
}
