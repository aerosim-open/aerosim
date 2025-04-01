use pyo3::prelude::*;
use pyo3::types::{PyCapsule, PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::{types::PyTypeSupport, AerosimMessage};

#[pyclass(get_all)]
#[derive(
    Clone,
    Copy,
    Debug,
    Serialize,
    Deserialize,
    PartialEq,
    aerosim_macros::AerosimMessage,
    JsonSchema,
)]
pub struct Vector3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Default for Vector3 {
    fn default() -> Vector3 {
        Vector3 {
            x: 0.0,
            y: 0.0,
            z: 0.0,
        }
    }
}

#[pymethods]
impl Vector3 {
    #[new]
    #[pyo3(signature = (x=Vector3::default().x, y=Vector3::default().y, z=Vector3::default().z))]
    pub fn new(x: f64, y: f64, z: f64) -> Self {
        Vector3 { x, y, z }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.y)?;
        dict.set_item("z", self.z)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

#[pyclass(get_all, set_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, AerosimMessage, JsonSchema)]
pub struct Quaternion {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Default for Quaternion {
    fn default() -> Quaternion {
        Quaternion {
            w: 1.0,
            x: 0.0,
            y: 0.0,
            z: 0.0,
        }
    }
}

#[pymethods]
impl Quaternion {
    #[new]
    #[pyo3(signature = (w=Quaternion::default().w, x=Quaternion::default().x, y=Quaternion::default().y, z=Quaternion::default().z))]
    pub fn new(w: f64, x: f64, y: f64, z: f64) -> Self {
        Quaternion { w, x, y, z }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("w", self.w)?;
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.y)?;
        dict.set_item("z", self.z)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

#[pyclass(get_all, set_all)]
#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq, AerosimMessage, JsonSchema)]

pub struct Pose {
    pub position: Vector3,
    pub orientation: Quaternion,
}

#[pymethods]
impl Pose {
    #[new]
    pub fn new(position: Vector3, orientation: Quaternion) -> Self {
        Pose {
            position,
            orientation,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("position", self.position.to_dict(py)?)?;
        dict.set_item("orientation", self.orientation.to_dict(py)?)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

// Add tests for the geometry module
#[cfg(test)]

mod tests {

    #[test]
    fn test_vector3() {
        let v = crate::types::Vector3::new(1.0, 2.0, 3.0);
        assert_eq!(v.x, 1.0);
        assert_eq!(v.y, 2.0);
        assert_eq!(v.z, 3.0);
    }

    #[test]
    fn test_quaternion() {
        let q = crate::types::Quaternion::new(1.0, 2.0, 3.0, 4.0);
        assert_eq!(q.w, 1.0);
        assert_eq!(q.x, 2.0);
        assert_eq!(q.y, 3.0);
        assert_eq!(q.z, 4.0);
    }

    #[test]
    fn test_pose() {
        let position = crate::types::Vector3::new(1.0, 2.0, 3.0);
        let orientation = crate::types::Quaternion::new(1.0, 2.0, 3.0, 4.0);
        let p = crate::types::Pose::new(position, orientation);
        assert_eq!(p.position.x, 1.0);
        assert_eq!(p.position.y, 2.0);
        assert_eq!(p.position.z, 3.0);
        assert_eq!(p.orientation.w, 1.0);
        assert_eq!(p.orientation.x, 2.0);
        assert_eq!(p.orientation.y, 3.0);
        assert_eq!(p.orientation.z, 4.0);
    }
}
