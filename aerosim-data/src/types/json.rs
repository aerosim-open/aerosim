use schemars::JsonSchema;

use crate::types::PyTypeSupport;
use crate::AerosimMessage;

use pyo3::{exceptions::PyValueError, prelude::*, types::PyCapsule};
use pythonize::{depythonize, pythonize};

use serde::{Deserialize, Serialize};
use serde_json;

#[pyclass]
#[derive(
    Clone, Debug, Serialize, Deserialize, PartialEq, aerosim_macros::AerosimMessage, JsonSchema,
)]
pub struct JsonData {
    data: String,
}

impl JsonData {
    pub fn new(data: serde_json::Value) -> Self {
        JsonData {
            data: data.to_string(),
        }
    }

    pub fn get_data(&self) -> Option<serde_json::Value> {
        serde_json::from_str(&self.data).ok()
    }
}

#[pymethods]
impl JsonData {
    #[new]
    pub fn pynew(py: Python, data: PyObject) -> PyResult<Self> {
        let json: serde_json::Value = depythonize(&data.into_bound(py)).map_err(|e| {
            PyValueError::new_err(format!("Failed to deserialize from Python object: {}", e))
        })?;
        Ok(JsonData {
            data: json.to_string(),
        })
    }

    #[pyo3(name = "get_data")]
    pub fn pyget_data(&self, py: Python) -> PyResult<PyObject> {
        let json = self
            .get_data()
            .ok_or_else(|| PyValueError::new_err(format!("Failed to deserialize JSON data")))?;
        let obj = pythonize(py, &json).map_err(|e| {
            PyValueError::new_err(format!("Failed to serialize to Python object: {}", e))
        })?;
        Ok(obj.into())
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.pyget_data(py)
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
