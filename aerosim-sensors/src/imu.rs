use crate::{gnss::Vector3, Sensor};
use pyo3::{prelude::*, types::PyDict};

#[pyclass(extends=Sensor, get_all)]
#[derive(Clone, Copy, Debug)]
pub struct IMU {
    acceleration: Vector3,
    gyroscope: Vector3,
    magnetic_field: Vector3,
}

#[pymethods]
impl IMU {
    #[new]
    #[pyo3(signature = (acceleration=Vector3::default(), gyroscope=Vector3::default(), magnetic_field=Vector3::default()))]
    fn new(acceleration: Vector3, gyroscope: Vector3, magnetic_field: Vector3) -> (Self, Sensor) {
        (
            Self {
                acceleration,
                gyroscope,
                magnetic_field,
            },
            Sensor::new("IMU".to_string(), 0.0),
        )
    }

    pub fn update(
        &mut self,
        acceleration_x: f64,
        acceleration_y: f64,
        acceleration_z: f64,
        gyroscope_x: f64,
        gyroscope_y: f64,
        gyroscope_z: f64,
        magnetic_field_x: f64,
        magnetic_field_y: f64,
        magnetic_field_z: f64,
    ) {
        self.acceleration = Vector3::new(acceleration_x, acceleration_y, acceleration_z);
        self.gyroscope = Vector3::new(gyroscope_x, gyroscope_y, gyroscope_z);
        self.magnetic_field = Vector3::new(magnetic_field_x, magnetic_field_y, magnetic_field_z);
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("acceleration", self.acceleration.to_python_tuple())?;
        dict.set_item("gyroscope", self.gyroscope.to_python_tuple())?;
        dict.set_item("magnetic_field", self.magnetic_field.to_python_tuple())?;
        Ok(dict.into())
    }
}
