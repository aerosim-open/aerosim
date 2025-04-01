use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, Default, JsonSchema)]
pub struct GNSSPositionData {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: f64,
    pub velocity: f64,
    pub heading: f64,
    pub ground_velocity: f64,
    pub acceleration: f64,
}

#[pymethods]
impl GNSSPositionData {
    #[new]
    #[pyo3(signature = (latitude=0.0, longitude=0.0, altitude=0.0, velocity=0.0, heading=0.0, ground_velocity=0.0, acceleration=0.0))]
    pub fn new(
        latitude: f64,
        longitude: f64,
        altitude: f64,
        velocity: f64,
        heading: f64,
        ground_velocity: f64,
        acceleration: f64,
    ) -> Self {
        GNSSPositionData {
            latitude,
            longitude,
            altitude,
            velocity,
            heading,
            ground_velocity,
            acceleration,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("latitude", self.latitude)?;
        let _ = dict.set_item("longitude", self.longitude)?;
        let _ = dict.set_item("altitude", self.altitude)?;
        let _ = dict.set_item("velocity", self.velocity)?;
        let _ = dict.set_item("heading", self.heading)?;
        let _ = dict.set_item("ground_velocity", self.ground_velocity)?;
        let _ = dict.set_item("acceleration", self.acceleration)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
