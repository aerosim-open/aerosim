use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use super::types::{ADSBVersion, CapabilityClassAirborne, CapabilityClassSurface, OperationalMode};

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AircraftOperationStatusAirborne {
    pub capability_class: CapabilityClassAirborne,
    pub operational_mode: OperationalMode,
    pub version_number: ADSBVersion,
    pub nic_supplement_a: u8,
    pub navigational_accuracy_category: u8,
    pub geometric_vertical_accuracy: u8,
    pub source_integrity_level: u8,
    pub barometric_altitude_integrity: u8,
    pub horizontal_reference_direction: u8,
    pub sil_supplement: u8,
}

#[pymethods]
impl AircraftOperationStatusAirborne {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("capability_class", self.capability_class)?;
        let _ = dict.set_item("operational_mode", self.operational_mode)?;
        let _ = dict.set_item("version_number", self.version_number)?;
        let _ = dict.set_item("nic_supplement_a", self.nic_supplement_a)?;
        let _ = dict.set_item(
            "navigational_accuracy_category",
            self.navigational_accuracy_category,
        )?;
        let _ = dict.set_item(
            "geometric_vertical_accuracy",
            self.geometric_vertical_accuracy,
        )?;
        let _ = dict.set_item("source_integrity_level", self.source_integrity_level)?;
        let _ = dict.set_item(
            "barometric_altitude_integrity",
            self.barometric_altitude_integrity,
        )?;
        let _ = dict.set_item(
            "horizontal_reference_direction",
            self.horizontal_reference_direction,
        )?;
        let _ = dict.set_item("sil_supplement", self.sil_supplement)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AircraftOperationStatusSurface {
    pub capability_class: CapabilityClassSurface,
    pub lw_codes: u8,
    pub operational_mode: OperationalMode,
    pub gps_antenna_offset: u8,
    pub version_number: ADSBVersion,
    pub nic_supplement_a: u8,
    pub navigational_accuracy_category: u8,
    pub source_integrity_level: u8,
    pub barometric_altitude_integrity: u8,
    pub horizontal_reference_direction: u8,
    pub sil_supplement: u8,
}

#[pymethods]
impl AircraftOperationStatusSurface {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("capability_class", self.capability_class)?;
        let _ = dict.set_item("lw_codes", self.lw_codes)?;
        let _ = dict.set_item("operational_mode", self.operational_mode)?;
        let _ = dict.set_item("gps_antenna_offset", self.gps_antenna_offset)?;
        let _ = dict.set_item("version_number", self.version_number)?;
        let _ = dict.set_item("nic_supplement_a", self.nic_supplement_a)?;
        let _ = dict.set_item(
            "navigational_accuracy_category",
            self.navigational_accuracy_category,
        )?;
        let _ = dict.set_item("source_integrity_level", self.source_integrity_level)?;
        let _ = dict.set_item(
            "barometric_altitude_integrity",
            self.barometric_altitude_integrity,
        )?;
        let _ = dict.set_item(
            "horizontal_reference_direction",
            self.horizontal_reference_direction,
        )?;
        let _ = dict.set_item("sil_supplement", self.sil_supplement)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}
