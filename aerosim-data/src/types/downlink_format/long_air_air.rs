use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::adsb::types::ICAOAddress;

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct LongAirAir {
    pub icao: ICAOAddress,
    pub altitude: u16,
}

#[pymethods]
impl LongAirAir {
    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("icao", self.icao.to_hex());
        let _ = dict.set_item("altitude", self.altitude);
        Ok(dict.into())
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }
}
