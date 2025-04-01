pub mod adsb;
pub mod gnss;
pub mod imu;

use pyo3::prelude::*;

#[pyclass(subclass)]
#[derive(Clone, Debug)]
pub struct Sensor {
    #[pyo3(get, set)]
    pub name: String,
    pub value: f64,
}

#[pymethods]
impl Sensor {
    #[new]
    fn new(name: String, value: f64) -> Self {
        Sensor { name, value }
    }

    // Custom getter method
    fn get_value(&self) -> f64 {
        self.value
    }

    // Custom setter method
    fn set_value(&mut self, value: f64) {
        self.value = value;
    }
}

#[pyclass]
pub struct SensorManager {
    pub sensors: Vec<Sensor>,
}

#[pymethods]
impl SensorManager {
    #[new]
    fn new() -> Self {
        SensorManager {
            sensors: Vec::new(),
        }
    }

    fn add_sensor(&mut self, sensor: Sensor) {
        self.sensors.push(sensor);
    }

    fn get_sensor(&self, index: usize) -> Option<Sensor> {
        self.sensors.get(index).cloned()
    }

    fn get_all_sensors(&self) -> Vec<Sensor> {
        self.sensors.clone()
    }
}

#[pymodule]
fn _sensors(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Sensor>()?;
    m.add_class::<gnss::GNSS>()?;
    m.add_class::<imu::IMU>()?;
    m.add_class::<SensorManager>()?;

    let adsb = PyModule::new(_py, "adsb_functions")?;

    adsb.add_function(wrap_pyfunction!(adsb::decode::adsb_from_gnss_data, &adsb)?)?;
    adsb.add_function(wrap_pyfunction!(adsb::decode::message_to_string, &adsb)?)?;
    adsb.add_function(wrap_pyfunction!(adsb::decode::parse_message, &adsb)?)?;

    m.add_submodule(&adsb)?;

    Ok(())
}
