use aerosim_core::coordinate_system::world_coordinate::WorldCoordinate;
use aerosim_data::types::{ActorState, EffectorState, PrimaryFlightDisplayData};
use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Component, Serialize, Deserialize)]
pub struct ActorPropertiesComponent {
    pub actor_name: String,
    pub actor_asset: String,
    pub parent: String,
}

#[derive(Component, Serialize, Deserialize)]
pub struct ActorStateComponent {
    pub state: ActorState,
    pub world_coord: WorldCoordinate,
}

#[derive(Bundle)]
pub struct ActorBundle {
    pub actor_properties: ActorPropertiesComponent,
    pub actor_state: ActorStateComponent,
    pub ecs_transform: bevy_transform::components::Transform,
}

#[derive(Serialize, Deserialize)]
pub struct Effector {
    pub id: String,
    pub relative_path: String,
    pub state: EffectorState,
}

#[derive(Component, Serialize, Deserialize)]
pub struct EffectorsComponent {
    pub effectors: Vec<Effector>,
}

#[derive(Component, Serialize, Deserialize)]
pub struct PrimaryFlightDisplayComponent {
    pub pfd_data: PrimaryFlightDisplayData,
}
