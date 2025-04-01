use super::geometry::{Pose, Vector3};
use super::sensor::SensorType;
use super::vehicle::VehicleType;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
// PyO3 only supports unit variants for enums. Variant with data is not supported
pub enum ActorType {
    Vehicle(VehicleType),
    Sensor(SensorType),
}

// PyO3 only supports unit variants for enums so we need to use a struct instead
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct Actor {
    #[pyo3(get, set)]
    pub uid: u64,
    pub actor_type: ActorType,
    #[pyo3(get, set)]
    pub state: ActorState,
    #[pyo3(get, set)]
    pub model: ActorModel,
    #[pyo3(get, set)]
    pub parent_actor_uid: Option<u64>,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize, JsonSchema)]
#[pyclass(get_all)]
pub struct ActorState {
    pub pose: Pose,
}

#[pymethods]
impl ActorState {
    #[new]
    pub fn new(pose: Pose) -> Self {
        ActorState { pose }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("pose", self.pose.to_dict(py)?)?;
        Ok(dict.into())
    }

    pub fn __eq__(&self, other: &Self) -> bool {
        self.pose == other.pose
    }

    pub fn __ne__(&self, other: &Self) -> bool {
        self.pose != other.pose
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass(get_all, set_all)]
pub struct ActorModel {
    pub physical_properties: PhysicalProperties,
    pub asset_link: Option<String>,
}

#[pymethods]
impl ActorModel {
    #[new]
    #[pyo3(signature = (physical_properties, asset_link=None))]
    pub fn new(physical_properties: PhysicalProperties, asset_link: Option<String>) -> Self {
        ActorModel {
            physical_properties,
            asset_link,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("physical_properties", self.physical_properties.to_dict(py)?)?;
        dict.set_item("asset_link", self.asset_link.clone())?;
        Ok(dict.into())
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[pyclass(get_all, set_all)]
pub struct PhysicalProperties {
    pub mass: f64,
    pub inertia_tensor: Vector3,
    pub moment_of_inertia: Vector3,
}

#[pymethods]
impl PhysicalProperties {
    #[new]
    pub fn new(mass: f64, inertia_tensor: Vector3, moment_of_inertia: Vector3) -> Self {
        PhysicalProperties {
            mass,
            inertia_tensor,
            moment_of_inertia,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("mass", self.mass)?;
        dict.set_item("inertia_tensor", self.inertia_tensor.to_dict(py)?)?;
        dict.set_item("moment_of_inertia", self.moment_of_inertia.to_dict(py)?)?;
        Ok(dict.into())
    }
}
