use aerosim_data::types::{Vehicle, Pose};
use aerosim_data::middleware::{Middleware, ros2::ROS2Middleware};
use r2r::Node;
use std::sync::Arc;
use std::time::Duration;
use tokio::time;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let ctx = r2r::Context::create()?;
    let node = Arc::new(Node::create(ctx, "vehicle_publisher", "")?);
    let middleware = ROS2Middleware { node: node.clone() };

    let mut interval = time::interval(Duration::from_secs(1));

    let mut vehicle = Vehicle {
        id: "eVTOL_1".to_string(),
        vehicle_type: "eVTOL".to_string(),
        pose: Pose {
            position: [0.0, 0.0, 0.0],
            orientation: [0.0, 0.0, 0.0, 1.0],
        },
        velocity: 0.0,
        acceleration: 0.0,
    };

    loop {
        interval.tick().await;
        
        // Update vehicle position
        vehicle.pose.position[0] += 1.0;
        vehicle.pose.position[1] += 0.5;
        vehicle.pose.position[2] += 0.1;
        
        vehicle.velocity += 0.1;
        vehicle.acceleration += 0.01;

        middleware.publish("vehicle_topic", &vehicle).await?;
        println!("Published vehicle update: {:?}", vehicle);
    }
}