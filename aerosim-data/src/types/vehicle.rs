use crate::{types::PyTypeSupport, AerosimMessage};

use super::actor::ActorState;
use super::geometry::Vector3;
use pyo3::prelude::*;
use pyo3::types::{PyCapsule, PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use strum_macros::{Display, EnumString};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, EnumString, Display, PartialEq)]
#[pyclass(eq, eq_int)]
pub enum VehicleType {
    Ground,
    Aerial,
    Marine,
}

#[pymethods]
impl VehicleType {
    #[staticmethod]
    pub fn from_str(s: &str) -> PyResult<Self> {
        s.parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid VehicleType"))
    }

    pub fn __str__(&self) -> String {
        self.to_string()
    }

    pub fn __repr__(&self) -> String {
        format!("VehicleType::{}", self)
    }

    #[staticmethod]
    pub fn to_dict(py: Python) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        for variant in [
            VehicleType::Ground,
            VehicleType::Aerial,
            VehicleType::Marine,
        ] {
            dict.set_item(variant.to_string(), variant.__repr__())?;
        }
        Ok(dict.into())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, AerosimMessage, JsonSchema)]
#[pyclass(get_all)]
pub struct VehicleState {
    pub state: ActorState,
    pub velocity: Vector3,
    pub angular_velocity: Vector3,
    pub acceleration: Vector3,
    pub angular_acceleration: Vector3,
}

#[pymethods]
impl VehicleState {
    #[new]
    #[pyo3(signature = (state=ActorState::default(), velocity=Vector3::default(), angular_velocity=Vector3::default(), acceleration=Vector3::default(), angular_acceleration=Vector3::default()))]
    pub fn new(
        state: ActorState,
        velocity: Vector3,
        angular_velocity: Vector3,
        acceleration: Vector3,
        angular_acceleration: Vector3,
    ) -> Self {
        VehicleState {
            state,
            velocity,
            angular_velocity,
            acceleration,
            angular_acceleration,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("state", self.state.to_dict(py)?)?;
        dict.set_item("velocity", self.velocity.to_dict(py)?)?;
        dict.set_item("angular_velocity", self.angular_velocity.to_dict(py)?)?;
        dict.set_item("acceleration", self.acceleration.to_dict(py)?)?;
        dict.set_item(
            "angular_acceleration",
            self.angular_acceleration.to_dict(py)?,
        )?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
