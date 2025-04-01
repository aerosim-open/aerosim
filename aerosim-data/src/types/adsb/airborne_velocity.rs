use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[pyclass(get_all)]
#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AirborneVelocity {
    /// Velocity subtype
    pub st: u8,
    pub nac_v: u8,
    /// Source bit for vertical rate: 0: Barometric 1: Geometric
    pub vr_src: u8,
    /// Sign bit for vertical rate, 0: Up, 1: Down
    pub s_vr: u8,
    /// Vertical rate
    pub vr: u16,
    pub reserved: u8,
    /// Sign bit for GNSS and Baro altitudes difference. 0: GNSS alt above Baro alt, 1: GNSS alt below Baro alt
    pub s_dif: u8,
    /// Difference between GNSS and Baro altitudes
    pub d_alt: u16,
    /// Effective heading
    pub heading: Option<f32>,
    /// Effective ground speed
    pub ground_speed: Option<f64>,
    /// Effective vertical rate
    pub vertical_rate: Option<i16>,
}

#[pymethods]
impl AirborneVelocity {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("st", self.st)?;
        let _ = dict.set_item("nac_v", self.nac_v)?;
        if self.vr_src == 0 {
            let _ = dict.set_item("vr_src", "Barometric")?;
        } else {
            let _ = dict.set_item("vr_src", "Geometric")?;
        }
        let _ = dict.set_item("s_vr", self.s_vr)?;
        let _ = dict.set_item("vr", self.vr)?;
        let _ = dict.set_item("reserved", self.reserved)?;
        let _ = dict.set_item("s_dif", self.s_dif)?;
        let _ = dict.set_item("d_alt", self.d_alt)?;
        let _ = dict.set_item("heading", self.heading)?;
        let _ = dict.set_item("ground_speed", self.ground_speed)?;
        let _ = dict.set_item("vertical_rate", self.vertical_rate)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
