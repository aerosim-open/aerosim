use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Serialize, Deserialize)]
pub struct WorldOrigin {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: f64,
}

#[derive(Resource, Serialize, Deserialize)]
pub struct Weather
{
    pub preset: String,
}
