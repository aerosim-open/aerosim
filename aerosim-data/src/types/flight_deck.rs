use crate::{types::PyTypeSupport, AerosimMessage};
use pyo3::prelude::*;
use pyo3::types::{PyCapsule, PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_repr::{Deserialize_repr, Serialize_repr};
use strum_macros::{Display, EnumString};

#[derive(
    Debug,
    Clone,
    Copy,
    Serialize_repr,
    Deserialize_repr,
    EnumString,
    Display,
    PartialEq,
    AerosimMessage,
    JsonSchema,
)]
#[repr(u8)]
#[pyclass(eq, eq_int, get_all, set_all)]
pub enum HSIMode {
    GPS = 0,
    VOR1 = 1,
    VOR2 = 2,
}

#[pymethods]
impl HSIMode {
    pub fn __str__(&self) -> String {
        self.to_string()
    }

    pub fn __repr__(&self) -> String {
        format!("HSIMode::{}", self)
    }

    pub fn to_int(&self) -> i32 {
        *self as i32
    }

    #[staticmethod]
    pub fn to_dict(py: Python) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        for variant in [HSIMode::GPS, HSIMode::VOR1, HSIMode::VOR2] {
            dict.set_item(variant.to_string(), variant.to_int())?;
        }
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, AerosimMessage, JsonSchema)]
#[pyclass(get_all)]
pub struct PrimaryFlightDisplayData {
    pub airspeed_kts: f64,                    // JSBSim "velocities/vc-kts"
    pub true_airspeed_kts: f64,               // JSBSim "velocities/vtrue-kts"
    pub altitude_ft: f64,                     // JSBSim "position/h-sl-ft"
    pub target_altitude_ft: f64,              // AutopilotCommand "altitude_setpoint_ft"
    pub altimeter_pressure_setting_inhg: f64, // User-set value (standard pressure = 29.92 inHG, QNH = height above MSL adjusted from local atmospheric pressure, QFE = height above airfield elevation)
    pub vertical_speed_fpm: f64,              // JSBSim "velocities/h-dot-fps" converted to feet/min
    pub pitch_deg: f64,                       // JSBSim "attitude/pitch-rad"
    pub roll_deg: f64,                        // JSBSim "attitude/roll-rad"
    pub side_slip_fps2: f64,                  // JSBSim "accelerations/vdot-ft_sec2"
    pub heading_deg: f64,                     // JSBSim "attitude/heading-true-rad" converted to deg
    pub hsi_course_select_heading_deg: f64, // For GPS mode, calculated heading between prev and next waypoints
    pub hsi_course_deviation_deg: f64, // For GPS mode, nautical mile offset from course line converted as 5 NM = 12 deg
    pub hsi_mode: HSIMode,             // User-set mode, start with GPS only
}

impl Default for PrimaryFlightDisplayData {
    fn default() -> PrimaryFlightDisplayData {
        PrimaryFlightDisplayData {
            airspeed_kts: 0.0,
            true_airspeed_kts: 0.0,
            altitude_ft: 0.0,
            target_altitude_ft: 0.0,
            altimeter_pressure_setting_inhg: 29.92,
            vertical_speed_fpm: 0.0,
            pitch_deg: 0.0,
            roll_deg: 0.0,
            side_slip_fps2: 0.0,
            heading_deg: 0.0,
            hsi_course_select_heading_deg: 0.0,
            hsi_course_deviation_deg: 0.0,
            hsi_mode: HSIMode::GPS,
        }
    }
}

#[pymethods]
impl PrimaryFlightDisplayData {
    #[new]
    pub fn new() -> Self {
        PrimaryFlightDisplayData::default()
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("airspeed_kts", self.airspeed_kts)?;
        dict.set_item("true_airspeed_kts", self.true_airspeed_kts)?;
        dict.set_item("altitude_ft", self.altitude_ft)?;
        dict.set_item("target_altitude_ft", self.target_altitude_ft)?;
        dict.set_item(
            "altimeter_pressure_setting_inhg",
            self.altimeter_pressure_setting_inhg,
        )?;
        dict.set_item("vertical_speed_fpm", self.vertical_speed_fpm)?;
        dict.set_item("pitch_deg", self.pitch_deg)?;
        dict.set_item("roll_deg", self.roll_deg)?;
        dict.set_item("side_slip_fps2", self.side_slip_fps2)?;
        dict.set_item("heading_deg", self.heading_deg)?;
        dict.set_item(
            "hsi_course_select_heading_deg",
            self.hsi_course_select_heading_deg,
        )?;
        dict.set_item("hsi_course_deviation_deg", self.hsi_course_deviation_deg)?;
        dict.set_item("hsi_mode", self.hsi_mode.to_int())?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
