use tokio;

use std::error::Error;
use std::time::Duration;

use aerosim_data::middleware::{MiddlewareRegistry, Middleware};
use aerosim_data::types::Vector3;

async fn publish_vector3(registry: &MiddlewareRegistry, data: &Vector3) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("dds").unwrap();
    middleware.publish("vector3", data, None).await
}

#[tokio::main]
async fn main() {
    let registry = MiddlewareRegistry::new();
    let transport = registry.get("dds").unwrap();

    let mut interval = tokio::time::interval(Duration::from_secs(1));
    for _ in 0..30 {
        println!("Publishing");
        let vector = Vector3::new(1.0, 1.0, 1.0);
        let _ = publish_vector3(registry, &vector).await;
        interval.tick().await;
    };

    transport.shutdown();
}
