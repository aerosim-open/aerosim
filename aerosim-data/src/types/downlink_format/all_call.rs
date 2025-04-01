use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::adsb::types::{Capability, ICAOAddress};
#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AllCallReply {
    pub icao: ICAOAddress,
    pub capability: Capability,
}

#[pymethods]
impl AllCallReply {
    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("icao", self.icao.to_hex());
        let _ = dict.set_item("capability", self.capability);
        Ok(dict.into())
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }
}
