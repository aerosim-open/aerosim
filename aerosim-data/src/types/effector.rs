use crate::{types::PyTypeSupport, AerosimMessage};

use super::geometry::Pose;
use pyo3::prelude::*;
use pyo3::types::{PyCapsule, PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, AerosimMessage, JsonSchema)]
#[pyclass(get_all)]
pub struct EffectorState {
    pub pose: Pose,
}

#[pymethods]
impl EffectorState {
    #[new]
    #[pyo3(signature = (pose=Pose::default()))]
    pub fn new(pose: Pose) -> Self {
        EffectorState { pose }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("pose", self.pose.to_dict(py)?)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
