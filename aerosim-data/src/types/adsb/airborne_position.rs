use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use super::types::SurveillanceStatus;

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AirbornePosition {
    /// Type Code
    pub tc: u8,
    /// Surveillance Status
    pub ss: SurveillanceStatus,
    /// Single antenna flag
    pub saf: u8,
    /// Encoded altitude
    pub alt: Option<u16>,
    /// Time flag
    pub t: bool,
    /// CPR format. 0 = even, 1 = odd
    pub f: u8,
    /// TC 9-18: Barometric altitude, TC 19-22: GNSS altitude
    pub alt_source: u8,
    /// Encoded latitude
    pub lat_cpr: u32,
    /// Encoded longitude
    pub lon_cpr: u32,
}

#[pymethods]
impl AirbornePosition {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("tc", self.tc)?;
        let _ = dict.set_item("ss", self.ss as u8)?;
        let _ = dict.set_item("saf", self.saf)?;
        let _ = dict.set_item("alt", self.alt)?;
        let _ = dict.set_item("t", self.t)?;
        let _ = dict.set_item("f", self.f as u8)?;
        if self.alt_source == 0 {
            let _ = dict.set_item("alt_source", "Barometric")?;
        } else {
            let _ = dict.set_item("alt_source", "GNSS")?;
        }
        let _ = dict.set_item("lat_cpr", self.lat_cpr)?;
        let _ = dict.set_item("lon_cpr", self.lon_cpr)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
