use super::actor::Actor;
use crate::types::*;

pub trait Vehicle: Actor {
    fn get_vehicle_type(&self) -> VehicleType;
    
}

pub trait GroundVehicle: Vehicle {
    fn get_wheel_count(&self) -> u32;
    fn get_ground_clearance(&self) -> f64;
}

pub trait AerialVehicle: Vehicle {
    fn get_max_altitude(&self) -> f64;
    fn get_rotor_count(&self) -> u32;
}

pub trait MarineVehicle: Vehicle {
    fn get_draft(&self) -> f64;
    fn get_displacement(&self) -> f64;
}