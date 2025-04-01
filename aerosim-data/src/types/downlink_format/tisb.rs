use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::adsb::types::{ControlFieldType, ICAOAddress, ME};

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct TisB {
    pub control_type: ControlFieldType,
    pub aa: ICAOAddress,
    pub me: ME,
}

#[pymethods]
impl TisB {
    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("address_announced", self.aa.to_hex());
        let _ = dict.set_item("control_type", self.control_type);
        let _ = dict.set_item("message_extended_squitter", self.me.to_dict(py)?);
        Ok(dict.into())
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }
}
