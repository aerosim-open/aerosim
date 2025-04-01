use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct TargetStateAndStatusInformation {
    pub is_fms: bool,
    pub altitude: u32,
    pub qnh: f32,
    pub is_heading: bool,
    pub heading: f32,
    pub nacp: u8,
    pub nicbaro: u8,
    pub sil: u8,
    pub mode_validity: bool,
    pub autopilot: bool,
    pub vnac: bool,
    pub alt_hold: bool,
    pub imf: bool,
    pub approach: bool,
    pub tcas: bool,
    pub lnav: bool,
}

#[pymethods]
impl TargetStateAndStatusInformation {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("is_fms", self.is_fms)?;
        let _ = dict.set_item("altitude", self.altitude)?;
        let _ = dict.set_item("qnh", self.qnh)?;
        let _ = dict.set_item("is_heading", self.is_heading)?;
        let _ = dict.set_item("heading", self.heading)?;
        let _ = dict.set_item("nacp", self.nacp)?;
        let _ = dict.set_item("nicbaro", self.nicbaro)?;
        let _ = dict.set_item("sil", self.sil)?;
        let _ = dict.set_item("mode_validity", self.mode_validity)?;
        let _ = dict.set_item("autopilot", self.autopilot)?;
        let _ = dict.set_item("vnac", self.vnac)?;
        let _ = dict.set_item("alt_hold", self.alt_hold)?;
        let _ = dict.set_item("imf", self.imf)?;
        let _ = dict.set_item("approach", self.approach)?;
        let _ = dict.set_item("tcas", self.tcas)?;
        let _ = dict.set_item("lnav", self.lnav)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
