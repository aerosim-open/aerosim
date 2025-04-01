use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::TimeStamp;

const SENTINEL_SECONDS: i32 = i32::MIN;

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, JsonSchema)]
pub struct Metadata {
    pub topic: String,
    pub type_name: String,

    /// Discrete simulation time.
    /// A sentinel value {sec: i32::MIN, nanosec: 0} is set when the simulation time is not specified.
    pub timestamp_sim: TimeStamp,

    /// Absolute platform time since the Unix Epoch.
    pub timestamp_platform: TimeStamp,
}

#[pymethods]
impl Metadata {
    #[new]
    #[pyo3(signature = (topic, type_name, timestamp_sim=None, timestamp_platform=None))]
    pub fn new(
        topic: &str,
        type_name: &str,
        timestamp_sim: Option<TimeStamp>,
        timestamp_platform: Option<TimeStamp>,
    ) -> Self {
        Metadata {
            topic: topic.to_string(),
            type_name: type_name.to_string(),
            timestamp_sim: timestamp_sim.unwrap_or(TimeStamp::new(SENTINEL_SECONDS, 0)),
            timestamp_platform: timestamp_platform.unwrap_or(TimeStamp::now()),
        }
    }

    pub fn is_sim_time_valid(&self) -> bool {
        self.timestamp_sim.sec >= 0
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("topic", self.topic.clone())?;
        dict.set_item("type_name", self.type_name.clone())?;
        dict.set_item("timestamp_sim", self.timestamp_sim.to_dict(py)?)?;
        dict.set_item("timestamp_platform", self.timestamp_platform.to_dict(py)?)?;
        Ok(dict.into())
    }
}
