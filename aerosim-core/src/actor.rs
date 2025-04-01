use pyo3::prelude::*;

use crate::math::rotator::Rotator;
use aerosim_data::types::geometry::Vector3;

#[pyclass]
#[derive(Clone, Debug)]
pub struct Actor {
    #[pyo3(get, set)]
    uid: u64, // unique id identifier for this actor
    #[pyo3(get, set)]
    actor_name: String, // actor name
    #[pyo3(get, set)]
    actor_type: u64, // identifier for actor type
    #[pyo3(get, set)]
    semantics: String, // Semantics of this actor
    #[pyo3(get, set)]
    latitude: f64, // latitude for this actor // We maybe do not want this and we have to remove it, we will need to discuss how are we gonna manage internally poses
    #[pyo3(get, set)]
    longitude: f64, // longitude for this actor // We maybe do not want this and we have to remove it, we will need to discuss how are we gonna manage internally poses
    #[pyo3(get, set)]
    altitude: f64, // altitude for this actor // We maybe do not want this and we have to remove it, we will need to discuss how are we gonna manage internally poses
    #[pyo3(get, set)]
    position: Vector3, // Position of this actor x y z meters from world origin
    #[pyo3(get, set)]
    rotation: Rotator, // Rotation of this actor roll pitch yaw
    #[pyo3(get, set)]
    velocity_linear: Vector3, // Velocity vector of this actor in m/s
    #[pyo3(get, set)]
    velocity_angular: Vector3, // Velocity vector of this actor in rad/s
    #[pyo3(get, set)]
    mass: f64,  // Mass of this actor in kg
    #[pyo3(get, set)]
    parent_uid: u64,  // ID of the parent actor
}

#[pymethods]
impl Actor {
    #[new]
    #[pyo3(signature = (actor_name, actor_type, semantics, latitude=0.0, longitude=0.0, altitude=0.0, position=Vector3{x: 0.0, y: 0.0, z: 0.0}, rotation=Rotator{yaw: 0.0, pitch: 0.0, roll: 0.0}, velocity=Vector3{x: 0.0, y: 0.0, z: 0.0}, velocity_angular=Vector3{x: 0.0, y: 0.0, z: 0.0}, mass=0.0, parent_uid=u64::MAX))]
    pub fn new(actor_name: String, actor_type: u64, semantics: String, latitude: f64, longitude: f64, altitude: f64, position: Vector3, rotation: Rotator, velocity: Vector3, velocity_angular:Vector3, mass: f64, parent_uid: u64) -> Self {
        let actor = Actor {
            uid: u64::MAX,
            actor_name: actor_name,
            actor_type: actor_type,
            semantics: semantics,
            latitude: latitude,
            longitude: longitude,
            altitude: altitude,
            position: position,
            rotation: rotation,
            velocity_linear: velocity,
            velocity_angular: velocity_angular,
            mass: mass,
            parent_uid: parent_uid,
        };
        return actor;
    }
}