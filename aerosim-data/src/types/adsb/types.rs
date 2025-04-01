use pyo3::{prelude::*, types::PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use strum_macros::{Display, EnumString};

use crate::types::downlink_format::{
    all_call::AllCallReply,
    comm::{CommBAltitudeReply, CommBIdentityReply, ExtendedSquitterMilitaryApplication},
    long_air_air::LongAirAir,
    surveillance::{ShortAirAirSurveillance, SurveillanceAltitudeReply, SurveillanceIdentityReply},
    tisb::TisB,
};

use super::{
    airborne_position::AirbornePosition,
    airborne_velocity::AirborneVelocity,
    aircraft_identification::AircraftIdentification,
    aircraft_operation_status::{AircraftOperationStatusAirborne, AircraftOperationStatusSurface},
    aircraft_status::AircraftStatus,
    gnss_position_data::GNSSPositionData,
    surface_position::SurfacePosition,
    target_state_and_status_information::TargetStateAndStatusInformation,
};

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct ADSB {
    pub capability: Capability,
    pub icao: ICAOAddress,
    pub me: ME,
    pub pi: ICAOAddress,
}

impl ADSB {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("capability", self.capability);
        let _ = dict.set_item("icao", self.icao.to_hex());
        let _ = dict.set_item("message_extended_quitter", self.me.to_dict(py)?);
        let _ = dict.set_item("parity", self.pi.to_hex());
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub enum ME {
    AircraftIdentification(AircraftIdentification),
    AirbornePosition(AirbornePosition),
    SurfacePosition(SurfacePosition),
    AirborneVelocity(AirborneVelocity),
    AircraftStatus(AircraftStatus),
    AircraftOperationStatusAirborne(AircraftOperationStatusAirborne),
    AircraftOperationStatusSurface(AircraftOperationStatusSurface),
    TargetStateAndStatusInformation(TargetStateAndStatusInformation),
    NoPosition([u8; 6]),
    Reserved0([u8; 6]),
    Reserved1([u8; 6]),
    AircraftOperationalCoordination([u8; 6]),
    SurfaceSystemStatus([u8; 6]),
    AircraftOperationStatusReserved(u8, [u8; 5]),
}

impl ME {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        match self {
            Self::AircraftIdentification(message_type) => Ok(message_type.to_dict(py)?),
            Self::AirbornePosition(message_type) => Ok(message_type.to_dict(py)?),
            Self::SurfacePosition(message_type) => Ok(message_type.to_dict(py)?),
            Self::AirborneVelocity(message_type) => Ok(message_type.to_dict(py)?),
            Self::AircraftOperationStatusAirborne(message_type) => Ok(message_type.to_dict(py)?),
            Self::AircraftOperationStatusSurface(message_type) => Ok(message_type.to_dict(py)?),
            Self::TargetStateAndStatusInformation(message_type) => Ok(message_type.to_dict(py)?),
            Self::NoPosition(_) => Ok(py.None()),
            Self::Reserved0(_) => Ok(py.None()),
            Self::Reserved1(_) => Ok(py.None()),
            Self::AircraftOperationalCoordination(_) => Ok(py.None()),
            Self::SurfaceSystemStatus(_) => Ok(py.None()),
            Self::AircraftOperationStatusReserved(_, _) => Ok(py.None()),
            _ => Ok(py.None()),
        }
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(get_all)]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum ADSBMessageType {
    ShortAirAirSurveillance(ShortAirAirSurveillance),
    SurveillanceAltitudeReply(SurveillanceAltitudeReply),
    SurveillanceIdentityReply(SurveillanceIdentityReply),
    AllCallReply(AllCallReply),
    LongAirAir(LongAirAir),
    ADSB(ADSB),
    TisB(TisB),
    ExtendedSquitterMilitaryApplication(ExtendedSquitterMilitaryApplication),
    CommBAltitudeReply(CommBAltitudeReply),
    CommBIdentityReply(CommBIdentityReply),
    GNSSPositionData(GNSSPositionData),
}

impl ADSBMessageType {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        match self {
            Self::ShortAirAirSurveillance(message_type) => Ok(message_type.to_dict(py)?),
            Self::SurveillanceAltitudeReply(message_type) => Ok(message_type.to_dict(py)?),
            Self::SurveillanceIdentityReply(message_type) => Ok(message_type.to_dict(py)?),
            Self::AllCallReply(message_type) => Ok(message_type.to_dict(py)?),
            Self::LongAirAir(message_type) => Ok(message_type.to_dict(py)?),
            Self::ADSB(message_type) => Ok(message_type.to_dict(py)?),
            Self::TisB(message_type) => Ok(message_type.to_dict(py)?),
            Self::ExtendedSquitterMilitaryApplication(message_type) => {
                Ok(message_type.to_dict(py)?)
            }
            Self::CommBAltitudeReply(message_type) => Ok(message_type.to_dict(py)?),
            Self::CommBIdentityReply(message_type) => Ok(message_type.to_dict(py)?),
            Self::GNSSPositionData(message_type) => Ok(message_type.to_dict(py)?),
        }
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(eq, eq_int)]
#[derive(
    Copy, Clone, Debug, Serialize, Deserialize, EnumString, Display, PartialEq, Eq, JsonSchema,
)]
pub enum EmergencyState {
    None = 0,
    General = 1,
    Lifeguard = 2,
    MinimumFuel = 3,
    NoCommunication = 4,
    UnlawfulInterference = 5,
    DownedAircraft = 6,
    Reserved2 = 7,
}

impl From<u8> for EmergencyState {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::None,
            1 => Self::General,
            2 => Self::Lifeguard,
            3 => Self::MinimumFuel,
            4 => Self::NoCommunication,
            5 => Self::UnlawfulInterference,
            6 => Self::DownedAircraft,
            _ => Self::Reserved2,
        }
    }
}

#[pyclass(eq, eq_int)]
#[derive(
    Copy, Clone, Debug, Serialize, Deserialize, EnumString, Display, PartialEq, Eq, JsonSchema,
)]
pub enum ADSBVersion {
    DOC9871AppendixA,
    DOC9871AppendixB,
    DOC9871AppendixC,
}

impl From<u8> for ADSBVersion {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::DOC9871AppendixA,
            1 => Self::DOC9871AppendixB,
            2 => Self::DOC9871AppendixC,
            _ => Self::DOC9871AppendixA,
        }
    }
}

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct CapabilityClassAirborne {
    pub reserved0: u8,
    pub acas: u8,
    pub cdti: u8,
    pub reserved1: u8,
    pub arv: u8,
    pub ts: u8,
    pub tc: u8,
}

impl CapabilityClassAirborne {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("reserved0", self.reserved0);
        let _ = dict.set_item("acas", self.acas);
        let _ = dict.set_item("cdti", self.cdti);
        let _ = dict.set_item("reserved1", self.reserved1);
        let _ = dict.set_item("arv", self.arv);
        let _ = dict.set_item("ts", self.ts);
        let _ = dict.set_item("tc", self.tc);
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct CapabilityClassSurface {
    /// 0, 0 in current version, reserved as id for later versions
    pub reserved0: u8,
    /// Position Offset Applied
    pub poe: u8,
    /// Aircraft has ADS-B 1090ES Receive Capability
    pub es1090: u8,
    /// Class B2 Ground Vehicle transmitting with less than 70 watts
    pub b2_low: u8,
    /// Aircraft has ADS-B UAT Receive Capability
    pub uat_in: u8,
    /// Nagivation Accuracy Category for Velocity
    pub nac_v: u8,
    /// NIC Supplement used on the Surface
    pub nic_supplement_c: u8,
}

impl CapabilityClassSurface {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("reserved0", self.reserved0);
        let _ = dict.set_item("poe", self.poe);
        let _ = dict.set_item("es1090", self.es1090);
        let _ = dict.set_item("b2_low", self.b2_low);
        let _ = dict.set_item("uat_in", self.uat_in);
        let _ = dict.set_item("nac_v", self.nac_v);
        let _ = dict.set_item("nic_supplement_c", self.nic_supplement_c);
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct OperationalMode {
    /// (0, 0) in Version 2, reserved for other values
    pub reserved: u8,
    pub tcas_ra_active: bool,
    pub ident_switch_active: bool,
    pub reserved_recv_atc_service: bool,
    pub single_antenna_flag: bool,
    pub system_design_assurance: u8,
}

impl OperationalMode {
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("reserved", self.reserved);
        let _ = dict.set_item("tcas_ra_active", self.tcas_ra_active);
        let _ = dict.set_item("ident_switch_active", self.ident_switch_active);
        let _ = dict.set_item("reserved_recv_atc_service", self.reserved_recv_atc_service);
        let _ = dict.set_item("single_antenna_flag", self.single_antenna_flag);
        let _ = dict.set_item("system_design_assurance", self.system_design_assurance);
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[pyclass(eq, eq_int)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, EnumString, Display, PartialEq, Eq)]
pub enum AirborneVelocitySubType {
    Reserved,
    GroundSpeedDecoding,
    AirspeedDecoding,
}

#[pyclass]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, PartialEq, Eq, JsonSchema)]
pub struct ICAOAddress(pub [u8; 3]);

impl ICAOAddress {
    pub fn to_hex(&self) -> String {
        format!("{:02X}{:02X}{:02X}", self.0[0], self.0[1], self.0[2])
    }

    pub fn from_u32(value: u32) -> Self {
        let bytes = value.to_be_bytes();
        Self([bytes[1], bytes[2], bytes[3]])
    }
}

#[pyclass(eq, eq_int)]
#[derive(Debug, PartialEq, Eq, Copy, Clone, Serialize, Deserialize, JsonSchema)]
pub enum FlightStatus {
    NoAlertNoSPIAirborne,
    NoAlertNoSPIOnGround,
    AlertNoSPIAirborne,
    AlertNoSPIOnGround,
    AlertSPIAirborneGround,
    NoAlertSPIAirborneGround,
    Reserved,
    NotAssigned,
}

impl From<u8> for FlightStatus {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::NoAlertNoSPIAirborne,
            1 => Self::NoAlertNoSPIOnGround,
            2 => Self::AlertNoSPIAirborne,
            3 => Self::AlertNoSPIOnGround,
            4 => Self::AlertSPIAirborneGround,
            5 => Self::NoAlertSPIAirborneGround,
            6 => Self::Reserved,
            _ => Self::NotAssigned,
        }
    }
}

#[pyclass(eq, eq_int)]
#[derive(Debug, PartialEq, Eq, Copy, Clone, Serialize, Deserialize, JsonSchema)]
pub enum Capability {
    Uncertain = 0,
    Reserved = 1,
    Ground = 4,
    Airborne = 5,
    Uncertain2 = 6,
    Uncertain3 = 7,
}

impl From<u8> for Capability {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::Uncertain,
            1 => Self::Reserved,
            4 => Self::Ground,
            5 => Self::Airborne,
            6 => Self::Uncertain2,
            7 => Self::Uncertain3,
            _ => Self::Uncertain,
        }
    }
}

#[pyclass(eq, eq_int)]
#[derive(Debug, PartialEq, Eq, Copy, Clone, Serialize, Deserialize, JsonSchema)]
#[allow(non_camel_case_types)]
pub enum ControlFieldType {
    ADSB_ES_NT,
    ADSB_ES_NT_ALT,
    TISB_FINE,
    TISB_COARSE,
    TISB_MANAGE,
    TISB_ADSB_RELAY,
    TISB_ADSB,
    Reserved,
}

impl From<u8> for ControlFieldType {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::ADSB_ES_NT,
            1 => Self::ADSB_ES_NT_ALT,
            2 => Self::TISB_FINE,
            3 => Self::TISB_COARSE,
            4 => Self::TISB_MANAGE,
            5 => Self::TISB_ADSB_RELAY,
            6 => Self::TISB_ADSB,
            _ => Self::Reserved,
        }
    }
}

#[pyclass(eq, eq_int)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, EnumString, PartialEq, Eq, JsonSchema)]
pub enum SurveillanceStatus {
    NoCondition,
    PermanentAlert,
    TemporaryAlert,
    SPICondition,
}

#[pymethods]
impl SurveillanceStatus {
    pub fn __str__(&self) -> String {
        self.to_string()
    }

    pub fn __repr__(&self) -> String {
        self.to_string()
    }

    pub fn to_string(&self) -> String {
        match self {
            Self::NoCondition => "No condition".to_string(),
            Self::PermanentAlert => "Permanent alert".to_string(),
            Self::TemporaryAlert => "Temporary alert".to_string(),
            Self::SPICondition => "SPI condition".to_string(),
        }
    }
}

impl From<u8> for SurveillanceStatus {
    fn from(value: u8) -> Self {
        match value {
            0 => Self::NoCondition,
            1 => Self::PermanentAlert,
            2 => Self::TemporaryAlert,
            3 => Self::SPICondition,
            _ => Self::NoCondition,
        }
    }
}
