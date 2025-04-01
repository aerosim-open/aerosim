use tokio;

use std::error::Error;
use std::time::Duration;

use serde_json;

use aerosim_data::middleware::{Middleware, MiddlewareRegistry};
use aerosim_data::types::{JsonData, Vector3};

async fn publish_vector3(registry: &MiddlewareRegistry, data: &Vector3) -> Result<(), Box<dyn Error>> {
    let middleware = registry.get("kafka").unwrap();
    middleware.publish("vector3", data, None).await
}

async fn publish_json(registry: &MiddlewareRegistry, data: &JsonData)-> Result<(), Box<dyn Error>> {
    let middleware = registry.get("kafka").unwrap();
    middleware.publish("json", data, None).await
}

#[tokio::main]
async fn main() {
    let registry = MiddlewareRegistry::new();

    let mut interval = tokio::time::interval(Duration::from_millis(100));
    loop {
        println!("Publishing");
        let vector = Vector3::new(1.0, 1.0, 1.0);
        let _ = publish_vector3(registry, &vector).await;

        let json = JsonData::new(serde_json::json!({
            "posx": 10,
            "posy": 20
        }));
        let _ = publish_json(registry, &json).await;

        interval.tick().await;
    };
}
