use aerosim_data::types::{
    adsb::{
        self,
        gnss_position_data::GNSSPositionData,
        types::{Capability, EmergencyState, FlightStatus, ICAOAddress, SurveillanceStatus, ME},
    },
    downlink_format::{
        all_call::AllCallReply,
        bds::{DataLinkCapability, BDS},
        comm::{
            CommBAltitudeReply, CommBIdentityReply, CommDExtendedLengthMessage,
            ExtendedSquitterMilitaryApplication,
        },
        long_air_air::LongAirAir,
        surveillance::{
            ShortAirAirSurveillance, SurveillanceAltitudeReply, SurveillanceIdentityReply,
        },
        DownlinkFormat,
    },
    sensor::ADSB,
};

use adsb_deku::{deku::DekuContainerRead, Frame, DF};
use pyo3::prelude::*;

#[pyfunction]
pub fn message_to_string(message: &str) -> PyResult<String> {
    let bytes = hex::decode(message)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid message"))?;
    let (_, frame) = Frame::from_bytes((&bytes[..], 0))
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid message"))?;
    Ok(frame.to_string())
}

#[pyfunction]
#[pyo3(signature = (latitude, longitude, altitude, velocity, heading, ground_velocity, acceleration))]
pub fn adsb_from_gnss_data(
    latitude: f64,
    longitude: f64,
    altitude: f64,
    velocity: f64,
    heading: f64,
    ground_velocity: f64,
    acceleration: f64,
) -> PyResult<ADSB> {
    let gnss_data = GNSSPositionData {
        latitude,
        longitude,
        altitude,
        velocity,
        heading,
        ground_velocity,
        acceleration,
    };
    let message = DownlinkFormat::GNSSPositionData(gnss_data);
    Ok(ADSB { message })
}

#[pyfunction]
pub fn parse_message(message: &str) -> PyResult<ADSB> {
    let bytes = hex::decode(message)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid message"))?;
    let (_, frame) = Frame::from_bytes((&bytes[..], 0))
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid message"))?;

    let message = match frame.df {
        DF::ShortAirAirSurveillance { altitude, .. } => {
            DownlinkFormat::ShortAirAir(ShortAirAirSurveillance {
                icao: ICAOAddress::from_u32(frame.crc),
                altitude: altitude.0,
            })
        }
        DF::SurveillanceAltitudeReply { fs, ac, .. } => {
            DownlinkFormat::SurveillanceAltitude(SurveillanceAltitudeReply {
                icao: ICAOAddress::from_u32(frame.crc),
                altitude: ac.0,
                flight_status: FlightStatus::from(fs as u8),
            })
        }
        DF::SurveillanceIdentityReply { fs, id, .. } => {
            let fs = fs as u8;
            DownlinkFormat::SurveillanceIdentity(SurveillanceIdentityReply {
                icao: ICAOAddress::from_u32(frame.crc),
                identity: id.0,
                flight_status: FlightStatus::from(fs),
            })
        }
        DF::AllCallReply {
            capability, icao, ..
        } => DownlinkFormat::AllCall({
            AllCallReply {
                icao: ICAOAddress(icao.0),
                capability: Capability::from(capability as u8),
            }
        }),
        DF::LongAirAir { altitude, .. } => DownlinkFormat::LongAirAir(LongAirAir {
            icao: ICAOAddress::from_u32(frame.crc),
            altitude: altitude.0,
        }),
        DF::ADSB(adsb) => DownlinkFormat::ADSB({
            let capability = Capability::from(adsb.capability as u8);
            let icao = ICAOAddress(adsb.icao.0);
            let me = get_me_from_adsb(adsb.me);
            let pi = ICAOAddress(adsb.pi.0);
            adsb::types::ADSB {
                capability,
                icao,
                me,
                pi,
            }
        }),
        DF::TisB { cf, .. } => {
            let control_type = unsafe { get_control_type(&cf) };
            let me = get_me_from_adsb(cf.me);
            DownlinkFormat::TisB(aerosim_data::types::downlink_format::tisb::TisB {
                control_type,
                aa: ICAOAddress::from_u32(frame.crc),
                me,
            })
        }
        DF::ExtendedQuitterMilitaryApplication { .. } => {
            DownlinkFormat::ExtendedSquitterMilitaryApplication(
                ExtendedSquitterMilitaryApplication { reserved: 0 },
            )
        }

        DF::CommBAltitudeReply { bds, alt, .. } => DownlinkFormat::CommBAltitude({
            let bds: BDS = match bds {
                adsb_deku::bds::BDS::Empty(_) => BDS::Empty(),
                adsb_deku::bds::BDS::DataLinkCapability(dlc) => {
                    BDS::DataLinkCapability(DataLinkCapability {
                        continuation_flag: dlc.continuation_flag,
                        overlay_command_capability: dlc.overlay_command_capability,
                        acas: dlc.acas,
                        mode_s_subnetwork_version_number: dlc.mode_s_subnetwork_version_number,
                        transponder_enhanced_protocol_indicator: dlc
                            .transponder_enhanced_protocol_indicator,
                        mode_s_specific_services_capability: dlc
                            .mode_s_specific_services_capability,
                        uplink_elm_average_throughput_capability: dlc
                            .uplink_elm_average_throughput_capability,
                        downlink_elm: dlc.downlink_elm,
                        aircraft_identification_capability: dlc.aircraft_identification_capability,
                        squitter_capability_subfield: dlc.squitter_capability_subfield,
                        surveillance_identifier_code: dlc.surveillance_identifier_code,
                        common_usage_gicb_capability_report: dlc
                            .common_usage_gicb_capability_report,
                        reserved_acas: dlc.reserved_acas,
                        bit_array: dlc.bit_array,
                    })
                }
                adsb_deku::bds::BDS::AircraftIdentification(identification) => {
                    BDS::AircraftIdentification(identification)
                }
                adsb_deku::bds::BDS::Unknown(_) => BDS::Unknown(),
            };
            CommBAltitudeReply {
                icao: ICAOAddress::from_u32(frame.crc),
                altitude: alt.0,
                bds,
            }
        }),
        DF::CommBIdentityReply { id, bds, .. } => DownlinkFormat::CommBIdentity({
            let bds: BDS = match bds {
                adsb_deku::bds::BDS::Empty(_) => BDS::Empty(),
                adsb_deku::bds::BDS::DataLinkCapability(dlc) => {
                    BDS::DataLinkCapability(DataLinkCapability {
                        continuation_flag: dlc.continuation_flag,
                        overlay_command_capability: dlc.overlay_command_capability,
                        acas: dlc.acas,
                        mode_s_subnetwork_version_number: dlc.mode_s_subnetwork_version_number,
                        transponder_enhanced_protocol_indicator: dlc
                            .transponder_enhanced_protocol_indicator,
                        mode_s_specific_services_capability: dlc
                            .mode_s_specific_services_capability,
                        uplink_elm_average_throughput_capability: dlc
                            .uplink_elm_average_throughput_capability,
                        downlink_elm: dlc.downlink_elm,
                        aircraft_identification_capability: dlc.aircraft_identification_capability,
                        squitter_capability_subfield: dlc.squitter_capability_subfield,
                        surveillance_identifier_code: dlc.surveillance_identifier_code,
                        common_usage_gicb_capability_report: dlc
                            .common_usage_gicb_capability_report,
                        reserved_acas: dlc.reserved_acas,
                        bit_array: dlc.bit_array,
                    })
                }
                adsb_deku::bds::BDS::AircraftIdentification(identification) => {
                    BDS::AircraftIdentification(identification)
                }
                adsb_deku::bds::BDS::Unknown(_) => BDS::Unknown(),
            };
            CommBIdentityReply {
                icao: ICAOAddress::from_u32(frame.crc),
                squawk: id,
                bds,
            }
        }),
        DF::CommDExtendedLengthMessage { .. } => {
            DownlinkFormat::CommDExtendedLength(CommDExtendedLengthMessage {
                icao: ICAOAddress::from_u32(frame.crc),
            })
        }
    };

    Ok(ADSB { message })
}

fn get_me_from_adsb(deku_me: adsb_deku::adsb::ME) -> aerosim_data::types::adsb::types::ME {
    match deku_me {
        adsb_deku::adsb::ME::AircraftIdentification(me) => ME::AircraftIdentification(
            aerosim_data::types::adsb::aircraft_identification::AircraftIdentification {
                tc: me.tc as u8,
                ca: me.ca,
                cn: me.cn,
            },
        ),
        adsb_deku::adsb::ME::SurfacePosition(me) => {
            let mov = me.mov as u8;
            let s = match me.s {
                adsb_deku::adsb::StatusForGroundTrack::Valid => true,
                adsb_deku::adsb::StatusForGroundTrack::Invalid => false,
            };
            let trk = me.trk as u8;
            let t = me.t;
            let f = me.f as u8;
            let lat_cpr = me.lat_cpr;
            let lon_cpr = me.lon_cpr;

            ME::SurfacePosition(
                aerosim_data::types::adsb::surface_position::SurfacePosition {
                    mov,
                    s,
                    trk,
                    t,
                    f,
                    lat_cpr,
                    lon_cpr,
                },
            )
        }
        adsb_deku::adsb::ME::AirbornePositionBaroAltitude(me) => {

            ME::AirbornePosition(
                aerosim_data::types::adsb::airborne_position::AirbornePosition {
                    tc: me.tc as u8,
                    ss: SurveillanceStatus::from(me.ss as u8),
                    saf: me.saf_or_imf,
                    alt: me.alt,
                    t: me.t,
                    f: me.odd_flag as u8,
                    alt_source: 0,
                    lat_cpr: me.lat_cpr,
                    lon_cpr: me.lon_cpr,
                },
            )
        }
        adsb_deku::adsb::ME::AirbornePositionGNSSAltitude(me) => {
            ME::AirbornePosition(
                aerosim_data::types::adsb::airborne_position::AirbornePosition {
                    tc: me.tc as u8,
                    ss: SurveillanceStatus::from(me.ss as u8),
                    saf: me.saf_or_imf,
                    alt: me.alt,
                    t: me.t,
                    f: me.odd_flag as u8,
                    alt_source: 1,
                    lat_cpr: me.lat_cpr,
                    lon_cpr: me.lon_cpr,
                },
            )
        }
        adsb_deku::adsb::ME::AirborneVelocity(me) => {
            let st = me.st;
            let nac_v = me.nac_v;
            let vr_src = me.vrate_src as u8;
            let s_vr = me.vrate_sign as u8;
            let vr = me.vrate_value;
            let reserved = me.reverved;
            let s_dif = me.gnss_sign as u8;
            let d_alt = me.gnss_baro_diff;
            let result = me.calculate();
            let (heading, ground_speed, vertical_rate) = match result {
                Some((heading, ground_speed, vertical_rate)) => { (Some(heading), Some(ground_speed), Some(vertical_rate)) },
                None => { (None, None, None) },

            };
            ME::AirborneVelocity(adsb::airborne_velocity::AirborneVelocity {
                st,
                nac_v,
                vr_src,
                s_vr,
                vr,
                reserved,
                s_dif,
                d_alt,
                heading,
                ground_speed,
                vertical_rate,
            })
        }
        adsb_deku::adsb::ME::AircraftStatus(me) => {
            ME::AircraftStatus(aerosim_data::types::adsb::aircraft_status::AircraftStatus {
                emergency_state: EmergencyState::from(me.emergency_state as u8),
                squawk:me.squawk,
            })
        }
        adsb_deku::adsb::ME::TargetStateAndStatusInformation(me) => {
            ME::TargetStateAndStatusInformation(
                aerosim_data::types::adsb::target_state_and_status_information::TargetStateAndStatusInformation {
                    is_fms: me.is_fms,
                    altitude: me.altitude,
                    qnh: me.qnh,
                    is_heading: me.is_heading,
                    heading: me.heading,
                    nacp: me.nacp,
                    nicbaro: me.nicbaro,
                    sil: me.sil,
                    mode_validity: me.mode_validity,
                    autopilot: me.autopilot,
                    vnac: me.vnac,
                    alt_hold: me.alt_hold,
                    imf: me.imf,
                    approach: me.approach,
                    tcas: me.tcas,
                    lnav: me.lnav,
                },
            )
        }
        adsb_deku::adsb::ME::AircraftOperationStatus(adsb_deku::adsb::OperationStatus::Airborne(opstatus_airborne)) => {
            let capability_class = aerosim_data::types::adsb::types::CapabilityClassAirborne {
                reserved0: opstatus_airborne.capability_class.reserved0,
                acas: opstatus_airborne.capability_class.acas,
                cdti: opstatus_airborne.capability_class.cdti,
                reserved1: opstatus_airborne.capability_class.reserved1,
                arv: opstatus_airborne.capability_class.arv,
                ts: opstatus_airborne.capability_class.ts,
                tc: opstatus_airborne.capability_class.tc,
            };
            let operational_mode = unsafe { get_operational_mode(&opstatus_airborne.operational_mode) };

            ME::AircraftOperationStatusAirborne(
                aerosim_data::types::adsb::aircraft_operation_status::AircraftOperationStatusAirborne {
                    capability_class,
                    operational_mode,
                    version_number: adsb::types::ADSBVersion::from(opstatus_airborne.version_number as u8),
                    nic_supplement_a: opstatus_airborne.nic_supplement_a,
                    navigational_accuracy_category: opstatus_airborne.navigational_accuracy_category,
                    geometric_vertical_accuracy: opstatus_airborne.geometric_vertical_accuracy,
                    source_integrity_level: opstatus_airborne.source_integrity_level,
                    barometric_altitude_integrity: opstatus_airborne.barometric_altitude_integrity,
                    horizontal_reference_direction: opstatus_airborne.horizontal_reference_direction,
                    sil_supplement: opstatus_airborne.sil_supplement,
                },
            )
        }
        adsb_deku::adsb::ME::AircraftOperationStatus(adsb_deku::adsb::OperationStatus::Surface(opstatus_surface)) => {

            let capability_class = aerosim_data::types::adsb::types::CapabilityClassSurface {
                reserved0: opstatus_surface.capability_class.reserved0,
                poe: opstatus_surface.capability_class.poe,
                es1090: opstatus_surface.capability_class.es1090,
                b2_low: opstatus_surface.capability_class.b2_low,
                uat_in: opstatus_surface.capability_class.uat_in,
                nac_v: opstatus_surface.capability_class.nac_v,
                nic_supplement_c: opstatus_surface.capability_class.nic_supplement_c,
            };
            let operational_mode = unsafe { get_operational_mode(&opstatus_surface.operational_mode) };
            ME::AircraftOperationStatusSurface(
                aerosim_data::types::adsb::aircraft_operation_status::AircraftOperationStatusSurface {
                    capability_class,
                    lw_codes: opstatus_surface.lw_codes,
                    operational_mode,
                    gps_antenna_offset: opstatus_surface.gps_antenna_offset,
                    version_number: adsb::types::ADSBVersion::from(opstatus_surface.version_number as u8),
                    nic_supplement_a: opstatus_surface.nic_supplement_a,
                    navigational_accuracy_category: opstatus_surface.navigational_accuracy_category,
                    source_integrity_level: opstatus_surface.source_integrity_level,
                    barometric_altitude_integrity: opstatus_surface.barometric_altitude_integrity,
                    horizontal_reference_direction: opstatus_surface.horizontal_reference_direction,
                    sil_supplement: opstatus_surface.sil_supplement,
                },
            )
        }
        adsb_deku::adsb::ME::AircraftOperationStatus(adsb_deku::adsb::OperationStatus::Reserved(a, b)) => {
            ME::AircraftOperationStatusReserved(a, b)
        }
        adsb_deku::adsb::ME::AircraftOperationalCoordination(me) => {
            ME::AircraftOperationalCoordination(me)
        }
        adsb_deku::adsb::ME::SurfaceSystemStatus(me) => ME::SurfaceSystemStatus(me),
        adsb_deku::adsb::ME::NoPosition(me) => ME::NoPosition(me),
        adsb_deku::adsb::ME::Reserved0(me) => ME::Reserved0(me),
        adsb_deku::adsb::ME::Reserved1(me) => ME::Reserved1(me),
    }
}

unsafe fn get_operational_mode(
    operational_mode: &adsb_deku::adsb::OperationalMode,
) -> aerosim_data::types::adsb::types::OperationalMode {
    let base_ptr = operational_mode as *const adsb_deku::adsb::OperationalMode as *const u8;

    let reserved = std::ptr::read_unaligned(base_ptr);
    let tcas_ra_active = std::ptr::read_unaligned(base_ptr.add(1)) != 0;
    let ident_switch_active = std::ptr::read_unaligned(base_ptr.add(2)) != 0;
    let reserved_recv_atc_service = std::ptr::read_unaligned(base_ptr.add(3)) != 0;
    let single_antenna_flag = std::ptr::read_unaligned(base_ptr.add(4)) != 0;
    let system_design_assurance = std::ptr::read_unaligned(base_ptr.add(5));

    aerosim_data::types::adsb::types::OperationalMode {
        reserved,
        tcas_ra_active,
        ident_switch_active,
        reserved_recv_atc_service,
        single_antenna_flag,
        system_design_assurance,
    }
}

unsafe fn get_control_type(
    control_field: &adsb_deku::adsb::ControlField,
) -> aerosim_data::types::adsb::types::ControlFieldType {
    let base_ptr = control_field as *const adsb_deku::adsb::ControlField as *const u8;
    let t_value: u8 = std::ptr::read_unaligned(base_ptr);
    aerosim_data::types::adsb::types::ControlFieldType::from(t_value)
}
