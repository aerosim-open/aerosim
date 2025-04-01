use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct SurfacePosition {
    /// Aircraft ground speed
    pub mov: u8,
    /// Status for ground track, if true, the ground track is valid
    pub s: bool,
    /// Ground track is encoded with a precision of 360/128 degrees. Zero degrees represents an aircraft ground track that is aligned with the true north
    pub trk: u8,
    /// Time flag
    pub t: bool,
    /// CPR format. 0 = even, 1 = odd
    pub f: u8,
    /// Encoded latitude
    pub lat_cpr: u32,
    /// Encoded longitude
    pub lon_cpr: u32,
}

#[pymethods]
impl SurfacePosition {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("mov", self.mov)?;
        let _ = dict.set_item("s", self.s)?;
        let _ = dict.set_item("trk", self.trk)?;
        let _ = dict.set_item("t", self.t)?;
        let _ = dict.set_item("f", self.f as u8)?;
        let _ = dict.set_item("lat_cpr", self.lat_cpr)?;
        let _ = dict.set_item("lon_cpr", self.lon_cpr)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
