use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Component, Serialize, Deserialize)]
pub struct SensorComponent {
    pub sensor_name: String,
    pub sensor_type: String,
    pub sensor_parameters: SensorParameters,
}

#[derive(Serialize, Deserialize)]
pub struct RGBCameraParameters {
    pub resolution: (u32, u32),
    pub tick_rate: f64,
    pub fov: f32,
    pub near_clip: f32,
    pub far_clip: f32,
    pub capture_enabled: bool,
}

#[derive(Serialize, Deserialize)]
pub struct DepthSensorParameters {
    pub tick_rate: f64,
    pub resolution: (u32, u32),
    pub fov: f32,
    pub near_clip: f32,
    pub far_clip: f32,
}

#[derive(Serialize, Deserialize)]
pub enum SensorParameters {
    RGBCamera(RGBCameraParameters),
    DepthSensor(DepthSensorParameters),
}

#[derive(Serialize, Deserialize)]
pub struct ViewportConfig {
    pub instance_id: String,
    pub active_camera: String,
}

#[derive(Resource, Serialize, Deserialize)]
pub struct ViewportConfigs {
    pub viewport_configs: Vec<ViewportConfig>,
}