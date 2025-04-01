pub mod actor;
pub mod adsb;
pub mod controller;
pub mod downlink_format;
pub mod effector;
pub mod flight_deck;
pub mod geometry;
pub mod header;
pub mod json;
pub mod sensor;
pub mod timestamp;
pub mod trajectory;
pub mod vehicle;

// Re-export types so they can be used as aerosim_data::types::Type
pub use actor::{ActorModel, ActorState, ActorType, PhysicalProperties};
pub use controller::{
    AircraftEffectorCommand, AutopilotCommand, AutopilotFlightPlanCommand, FlightControlCommand,
};
pub use effector::EffectorState;
pub use flight_deck::PrimaryFlightDisplayData;
pub use geometry::{Pose, Quaternion, Vector3};
pub use header::Header;
pub use json::JsonData;
pub use sensor::CameraInfo;
pub use sensor::CompressedImage;
pub use sensor::Image;
pub use sensor::ImageEncoding;
pub use sensor::ImageFormat;
pub use sensor::SensorType;
use sensor::ADSB;
use sensor::GNSS;
use sensor::IMU;
pub use timestamp::TimeStamp;
pub use trajectory::TrajectoryVisualization;
pub use vehicle::VehicleState;
pub use vehicle::VehicleType;

#[macro_use]
mod registry;
pub use registry::TypeRegistry;

mod typesupport;
pub use typesupport::{PyTypeSupport, TypeSupport};

use serde::{Deserialize, Serialize};

pub trait AerosimMessage: Serialize + for<'de> Deserialize<'de> + Clone + Send + Sync {
    fn get_type_name() -> String;
}

register_types!(
    TimeStamp
    Vector3
    JsonData
    VehicleState
    EffectorState
    AutopilotCommand
    FlightControlCommand
    AircraftEffectorCommand
    PrimaryFlightDisplayData
    TrajectoryVisualization
    GNSS
    ADSB
    IMU
);
