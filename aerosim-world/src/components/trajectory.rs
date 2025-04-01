use aerosim_data::types::trajectory::TrajectoryVisualizationSettings;
use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Component, Serialize, Deserialize, Default, Debug)]
pub struct TrajectoryVisualizationComponent {
    pub settings: TrajectoryVisualizationSettings,
    pub user_defined_waypoints: TrajectoryVisualizationParametersWaypoints,
    pub future_trajectory: TrajectoryVisualizationParametersWaypoints,
}

#[derive(Component, Serialize, Deserialize, Default, Debug)]
pub struct TrajectoryVisualizationParametersWaypoints {
    pub waypoints: Vec<(f32, f32, f32)>,
}
