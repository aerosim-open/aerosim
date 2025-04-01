use pyo3::prelude::*;

pub mod interfaces;
pub mod types;

pub mod middleware;

pub use aerosim_macros::AerosimMessage;
pub use types::AerosimMessage;

#[pymodule]
fn _aerosim_data(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    let types_module = PyModule::new(py, "types")?;

    // Add classes to the types submodule
    types_module.add_class::<types::json::JsonData>()?;
    types_module.add_class::<types::timestamp::TimeStamp>()?;
    types_module.add_class::<types::header::Header>()?;
    types_module.add_class::<types::geometry::Vector3>()?;
    types_module.add_class::<types::geometry::Quaternion>()?;
    types_module.add_class::<types::geometry::Pose>()?;
    types_module.add_class::<types::sensor::CameraInfo>()?;
    types_module.add_class::<types::sensor::ImageEncoding>()?;
    types_module.add_class::<types::sensor::ImageFormat>()?;
    types_module.add_class::<types::sensor::CompressedImage>()?;
    types_module.add_class::<types::sensor::Image>()?;
    types_module.add_class::<types::sensor::GNSS>()?;
    types_module.add_class::<types::sensor::ADSB>()?;
    types_module.add_class::<types::sensor::IMU>()?;
    types_module.add_class::<types::actor::ActorState>()?;
    types_module.add_class::<types::actor::ActorModel>()?;
    types_module.add_class::<types::actor::PhysicalProperties>()?;
    types_module.add_class::<types::sensor::SensorType>()?;
    types_module.add_class::<types::vehicle::VehicleType>()?;
    types_module.add_class::<types::vehicle::VehicleState>()?;
    types_module.add_class::<types::effector::EffectorState>()?;
    types_module.add_class::<types::adsb::gnss_position_data::GNSSPositionData>()?;
    types_module.add_class::<types::downlink_format::DownlinkFormat>()?;
    types_module.add_class::<types::downlink_format::all_call::AllCallReply>()?;
    types_module.add_class::<types::downlink_format::bds::BDS>()?;
    types_module.add_class::<types::downlink_format::bds::DataLinkCapability>()?;
    types_module.add_class::<types::downlink_format::comm::CommBAltitudeReply>()?;
    types_module.add_class::<types::downlink_format::comm::CommBIdentityReply>()?;
    types_module.add_class::<types::downlink_format::comm::CommDExtendedLengthMessage>()?;
    types_module
        .add_class::<types::downlink_format::comm::ExtendedSquitterMilitaryApplication>()?;
    types_module.add_class::<types::downlink_format::long_air_air::LongAirAir>()?;
    types_module.add_class::<types::downlink_format::surveillance::ShortAirAirSurveillance>()?;
    types_module.add_class::<types::downlink_format::surveillance::SurveillanceAltitudeReply>()?;
    types_module.add_class::<types::downlink_format::surveillance::SurveillanceIdentityReply>()?;
    types_module.add_class::<types::downlink_format::tisb::TisB>()?;
    types_module.add_class::<types::adsb::airborne_position::AirbornePosition>()?;
    types_module.add_class::<types::adsb::airborne_velocity::AirborneVelocity>()?;
    types_module.add_class::<types::adsb::aircraft_identification::AircraftIdentification>()?;
    types_module
        .add_class::<types::adsb::aircraft_operation_status::AircraftOperationStatusAirborne>()?;
    types_module
        .add_class::<types::adsb::aircraft_operation_status::AircraftOperationStatusSurface>()?;
    types_module.add_class::<types::adsb::aircraft_status::AircraftStatus>()?;
    types_module.add_class::<types::adsb::surface_position::SurfacePosition>()?;
    types_module.add_class::<types::adsb::target_state_and_status_information::TargetStateAndStatusInformation>()?;
    types_module.add_class::<types::adsb::types::ADSB>()?;
    types_module.add_class::<types::adsb::types::ADSBMessageType>()?;
    types_module.add_class::<types::adsb::types::ADSBVersion>()?;
    types_module.add_class::<types::adsb::types::AirborneVelocitySubType>()?;
    types_module.add_class::<types::adsb::types::Capability>()?;
    types_module.add_class::<types::adsb::types::CapabilityClassAirborne>()?;
    types_module.add_class::<types::adsb::types::CapabilityClassSurface>()?;
    types_module.add_class::<types::adsb::types::ControlFieldType>()?;
    types_module.add_class::<types::adsb::types::EmergencyState>()?;
    types_module.add_class::<types::adsb::types::ICAOAddress>()?;
    types_module.add_class::<types::adsb::types::ME>()?;
    types_module.add_class::<types::adsb::types::OperationalMode>()?;
    types_module.add_class::<types::adsb::types::SurveillanceStatus>()?;
    types_module.add_class::<types::controller::AutopilotFlightPlanCommand>()?;
    types_module.add_class::<types::controller::AutopilotCommand>()?;
    types_module.add_class::<types::controller::FlightControlCommand>()?;
    types_module.add_class::<types::controller::AircraftEffectorCommand>()?;
    types_module.add_class::<types::trajectory::TrajectoryVisualization>()?;
    types_module.add_class::<types::trajectory::TrajectoryVisualizationSettings>()?;
    types_module.add_class::<types::flight_deck::PrimaryFlightDisplayData>()?;
    types_module.add_class::<types::trajectory::TrajectoryWaypoints>()?;

    // Add the types submodule to the main module
    m.add_submodule(&types_module)?;

    // Add middleware
    let middleware_module = PyModule::new(py, "middleware")?;

    // Add classes to the middleware submodule
    middleware_module.add_class::<middleware::Metadata>()?;

    #[cfg(feature = "kafka")]
    middleware_module.add_class::<middleware::kafka::KafkaMiddleware>()?;
    #[cfg(feature = "dds")]
    middleware_module.add_class::<middleware::dds::DDSMiddleware>()?;

    #[cfg(feature = "kafka")]
    middleware_module.add_class::<middleware::kafka::KafkaSerializer>()?;
    #[cfg(feature = "kafka")]
    middleware_module.add_class::<middleware::kafka::BincodeSerializer>()?;
    #[cfg(feature = "dds")]
    middleware_module.add_class::<middleware::dds::DDSSerializer>()?;

    // Add the types submodule to the main module
    m.add_submodule(&middleware_module)?;

    Ok(())
}
