use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::adsb::types::ICAOAddress;
use crate::types::downlink_format::bds::BDS;

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct ExtendedSquitterMilitaryApplication {
    pub reserved: u8,
}

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct CommBAltitudeReply {
    pub icao: ICAOAddress,
    pub altitude: u16,
    pub bds: BDS,
}

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct CommBIdentityReply {
    pub icao: ICAOAddress,
    pub squawk: u32,
    pub bds: BDS,
}

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct CommDExtendedLengthMessage {
    pub icao: ICAOAddress,
}

#[pymethods]
impl CommBAltitudeReply {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("icao", self.icao.to_hex());
        let _ = dict.set_item("altitude", self.altitude);
        let _ = dict.set_item("bds", self.bds.to_dict(py)?);
        Ok(dict.into())
    }
}

#[pymethods]
impl CommBIdentityReply {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("icao", self.icao.to_hex());
        let _ = dict.set_item("squawk", self.squawk);
        let _ = dict.set_item("bds", self.bds.to_dict(py)?);
        Ok(dict.into())
    }
}

#[pymethods]
impl CommDExtendedLengthMessage {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("icao", self.icao.to_hex());
        Ok(dict.into())
    }
}

#[pymethods]
impl ExtendedSquitterMilitaryApplication {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        self.__dict__(py)
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("reserved", self.reserved);
        Ok(dict.into())
    }
}
