use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[pyclass(eq)]
#[derive(Debug, PartialEq, Eq, Clone, Serialize, Deserialize, JsonSchema)]
pub enum BDS {
    Empty(),
    DataLinkCapability(DataLinkCapability),
    AircraftIdentification(String),
    Unknown(),
}

#[pyclass(get_all)]
#[derive(Copy, Debug, PartialEq, Eq, Clone, Serialize, Deserialize, JsonSchema)]
pub struct DataLinkCapability {
    pub continuation_flag: bool,
    pub overlay_command_capability: bool,
    pub acas: bool,
    pub mode_s_subnetwork_version_number: u8,
    pub transponder_enhanced_protocol_indicator: bool,
    pub mode_s_specific_services_capability: bool,
    pub uplink_elm_average_throughput_capability: u8,
    pub downlink_elm: u8,
    pub aircraft_identification_capability: bool,
    pub squitter_capability_subfield: bool,
    pub surveillance_identifier_code: bool,
    pub common_usage_gicb_capability_report: bool,
    pub reserved_acas: u8,
    pub bit_array: u16,
}

#[pymethods]
impl BDS {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        match self {
            Self::Empty() => {
                let _ = dict.set_item("type", "empty");
            }
            Self::AircraftIdentification(s) => {
                let _ = dict.set_item("type", "aircraft_identification");
                let _ = dict.set_item("ident", s);
            }
            Self::DataLinkCapability(dlc) => {
                let _ = dict.set_item("type", "datalink_capability");
                let _ = dict.set_item("datalink_capability", dlc.to_dict(py)?);
            }
            Self::Unknown() => {
                let _ = dict.set_item("type", "unknown");
            }
        }
        Ok(dict.into())
    }
}

#[pymethods]
impl DataLinkCapability {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("continuation_flag", self.continuation_flag);
        let _ = dict.set_item(
            "overlay_command_capability",
            self.overlay_command_capability,
        );
        let _ = dict.set_item("acas", self.acas);
        let _ = dict.set_item(
            "mode_s_subnetwork_version_number",
            self.mode_s_subnetwork_version_number,
        );
        let _ = dict.set_item(
            "transponder_enhanced_protocol_indicator",
            self.transponder_enhanced_protocol_indicator,
        );
        let _ = dict.set_item(
            "mode_s_specific_services_capability",
            self.mode_s_specific_services_capability,
        );
        let _ = dict.set_item(
            "uplink_elm_average_throughput_capability",
            self.uplink_elm_average_throughput_capability,
        );
        let _ = dict.set_item("downlink_elm", self.downlink_elm);
        let _ = dict.set_item(
            "aircraft_identification_capability",
            self.aircraft_identification_capability,
        );
        let _ = dict.set_item(
            "squitter_capability_subfield",
            self.squitter_capability_subfield,
        );
        let _ = dict.set_item(
            "surveillance_identifier_code",
            self.surveillance_identifier_code,
        );
        let _ = dict.set_item(
            "common_usage_gicb_capability_report",
            self.common_usage_gicb_capability_report,
        );
        let _ = dict.set_item("reserved_acas", self.reserved_acas);
        let _ = dict.set_item("bit_array", self.bit_array);
        Ok(dict.into())
    }
}
