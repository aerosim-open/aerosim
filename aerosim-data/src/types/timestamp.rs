use crate::AerosimMessage;
use crate::types::PyTypeSupport;

use chrono::{DateTime, Utc};
use pyo3::{
    prelude::*,
    types::{PyDict, PyCapsule}
};
use schemars::JsonSchema;

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq, Hash, PartialOrd, Ord, JsonSchema)]
#[derive(aerosim_macros::AerosimMessage)]
pub struct TimeStamp {
    pub sec: i32,
    pub nanosec: u32,
}

#[pymethods]
impl TimeStamp {
    #[new]
    pub fn new(sec: i32, nanosec: u32) -> Self {
        TimeStamp { sec, nanosec }
    }

    #[staticmethod]
    pub fn from_sec(sec: f64) -> Self {
        TimeStamp {
            sec: sec.trunc() as i32,
            nanosec: (sec.fract() * 1e9) as u32,
        }
    }

    pub fn to_sec(&self) -> f64 {
        self.sec as f64 + self.nanosec as f64 * 1e-9
    }

    #[staticmethod]
    pub fn from_millis(millisec: u64) -> Self {
        let dur = Duration::from_millis(millisec);
        TimeStamp {
            sec: dur.as_secs() as i32,
            nanosec: dur.subsec_nanos(),
        }
    }

    pub fn to_millis(&self) -> u64 {
        self.sec as u64 * 1e3 as u64 + self.nanosec as u64 / 1e6 as u64
    }

    #[staticmethod]
    pub fn from_nanos(nanosec: u64) -> Self {
        let dur = Duration::from_nanos(nanosec);
        TimeStamp {
            sec: dur.as_secs() as i32,
            nanosec: dur.subsec_nanos(),
        }
    }

    pub fn to_nanos(&self) -> u64 {
        self.sec as u64 * 1e9 as u64 + self.nanosec as u64
    }

    // Create a new TimeStamp from current time
    #[staticmethod]
    pub fn now() -> Self {
        let now: DateTime<Utc> = Utc::now();
        TimeStamp {
            sec: now.timestamp() as i32,           // Seconds since epoch
            nanosec: now.timestamp_subsec_nanos(), // Nanoseconds since last second
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("sec", self.sec)?;
        dict.set_item("nanosec", self.nanosec)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
