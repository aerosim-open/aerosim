use pyo3::{
    prelude::*,
    types::{PyCapsule, PyDict, PyList},
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_repr::{Deserialize_repr, Serialize_repr};
use strum_macros::{Display, EnumString};

use crate::{types::PyTypeSupport, AerosimMessage};

// ----------------------------------------------------------------------------
// Autopilot Flight Plan State
// Modes of autopilot flight plan execution

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
pub enum AutopilotFlightPlanCommand {
    Stop = 0,
    Run = 1,
    Pause = 2,
}

#[pymethods]
impl AutopilotFlightPlanCommand {
    #[staticmethod]
    pub fn from_str(s: &str) -> PyResult<Self> {
        s.parse().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid AutopilotFlightPlanCommand")
        })
    }

    pub fn __str__(&self) -> String {
        self.to_string()
    }

    pub fn __repr__(&self) -> String {
        format!("AutopilotFlightPlanCommand::{}", self)
    }

    pub fn to_int(&self) -> i32 {
        *self as i32
    }

    #[staticmethod]
    pub fn to_dict(py: Python) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        for variant in [
            AutopilotFlightPlanCommand::Stop,
            AutopilotFlightPlanCommand::Run,
            AutopilotFlightPlanCommand::Pause,
        ] {
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
#[pyclass(get_all, set_all)]
pub struct AutopilotCommand {
    pub flight_plan: String, // some kind of flight plan, e.g. waypoints, mission, etc. (JSON?)
    pub flight_plan_command: AutopilotFlightPlanCommand, // flight plan execution command
    pub use_manual_setpoints: bool, // flag to use manual setpoints instead of flight plan
    pub attitude_hold: bool, // flag to fix current attitude roll/pitch/yaw
    pub altitude_hold: bool, // flag to control to altitude setpoint
    pub altitude_setpoint_ft: f64, // altitude setpoint in feet
    pub airspeed_hold: bool, // flag to control to airspeed setpoint
    pub airspeed_setpoint_kts: f64, // airspeed setpoint in knots
    pub heading_hold: bool,  // flag to control to target heading
    pub heading_set_by_waypoint: bool, // flag to use waypoint as target heading instead of heading_setpoint
    pub heading_setpoint_deg: f64, // heading setpoint in degrees (0 = north, 90 = east, 180 = south, 270 = west)
    pub target_wp_latitude_deg: f64, // target waypoint latitude in degrees
    pub target_wp_longitude_deg: f64, // target waypoint longitude in degrees
}

impl Default for AutopilotCommand {
    fn default() -> AutopilotCommand {
        AutopilotCommand {
            flight_plan: "".to_string(),
            flight_plan_command: AutopilotFlightPlanCommand::Stop,
            use_manual_setpoints: false,
            attitude_hold: false,
            altitude_hold: false,
            altitude_setpoint_ft: 0.0,
            airspeed_hold: false,
            airspeed_setpoint_kts: 0.0,
            heading_hold: false,
            heading_set_by_waypoint: false,
            heading_setpoint_deg: 0.0,
            target_wp_latitude_deg: 0.0,
            target_wp_longitude_deg: 0.0,
        }
    }
}

// ----------------------------------------------------------------------------
// Autopilot Command
// Input to autopilot

#[pymethods]
impl AutopilotCommand {
    #[new]
    #[pyo3(signature = (
        flight_plan=AutopilotCommand::default().flight_plan,
        flight_plan_command=AutopilotCommand::default().flight_plan_command,
        use_manual_setpoints=AutopilotCommand::default().use_manual_setpoints,
        attitude_hold=AutopilotCommand::default().attitude_hold,
        altitude_hold=AutopilotCommand::default().altitude_hold,
        altitude_setpoint_ft=AutopilotCommand::default().altitude_setpoint_ft,
        airspeed_hold=AutopilotCommand::default().airspeed_hold,
        airspeed_setpoint_kts=AutopilotCommand::default().airspeed_setpoint_kts,
        heading_hold=AutopilotCommand::default().heading_hold,
        heading_set_by_waypoint=AutopilotCommand::default().heading_set_by_waypoint,
        heading_setpoint_deg=AutopilotCommand::default().heading_setpoint_deg,
        target_wp_latitude_deg=AutopilotCommand::default().target_wp_latitude_deg,
        target_wp_longitude_deg=AutopilotCommand::default().target_wp_longitude_deg
    ))]
    pub fn new(
        flight_plan: String,
        flight_plan_command: AutopilotFlightPlanCommand,
        use_manual_setpoints: bool,
        attitude_hold: bool,
        altitude_hold: bool,
        altitude_setpoint_ft: f64,
        airspeed_hold: bool,
        airspeed_setpoint_kts: f64,
        heading_hold: bool,
        heading_set_by_waypoint: bool,
        heading_setpoint_deg: f64,
        target_wp_latitude_deg: f64,
        target_wp_longitude_deg: f64,
    ) -> Self {
        AutopilotCommand {
            flight_plan,
            flight_plan_command,
            use_manual_setpoints,
            attitude_hold,
            altitude_hold,
            altitude_setpoint_ft,
            airspeed_hold,
            airspeed_setpoint_kts,
            heading_hold,
            heading_set_by_waypoint,
            heading_setpoint_deg,
            target_wp_latitude_deg,
            target_wp_longitude_deg,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("flight_plan", &self.flight_plan)?;
        dict.set_item("flight_plan_command", &self.flight_plan_command.to_int())?;
        dict.set_item("use_manual_setpoints", self.use_manual_setpoints)?;
        dict.set_item("attitude_hold", self.attitude_hold)?;
        dict.set_item("altitude_hold", self.altitude_hold)?;
        dict.set_item("altitude_setpoint_ft", self.altitude_setpoint_ft)?;
        dict.set_item("airspeed_hold", self.airspeed_hold)?;
        dict.set_item("airspeed_setpoint_kts", self.airspeed_setpoint_kts)?;
        dict.set_item("heading_hold", self.heading_hold)?;
        dict.set_item("heading_set_by_waypoint", self.heading_set_by_waypoint)?;
        dict.set_item("heading_setpoint_deg", self.heading_setpoint_deg)?;
        dict.set_item("target_wp_latitude_deg", self.target_wp_latitude_deg)?;
        dict.set_item("target_wp_longitude_deg", self.target_wp_longitude_deg)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

// ----------------------------------------------------------------------------
// Flight Control Command
// Output from (auto)pilot, input to flight controller

#[derive(Debug, Clone, Serialize, Deserialize, AerosimMessage, JsonSchema)]
#[pyclass(get_all, set_all)]
pub struct FlightControlCommand {
    power_cmd: Vec<f64>, // power, 0.0~1.0, array to be able to split vertical lift and horizontal cruise
    roll_cmd: f64,       // roll axis, -1.0~1.0
    pitch_cmd: f64,      // pitch axis, -1.0~1.0
    yaw_cmd: f64,        // yaw axis, -1.0~1.0
    thrust_tilt_cmd: f64, // tilt vtol, 0.0~1.0
    flap_cmd: f64,       // flap, 0.0~1.0, for low speed flight
    speedbrake_cmd: f64, // speedbrake, 0.0~1.0, for fixed-wing
    landing_gear_cmd: f64, // landing gear, 0.0 up ~ 1.0 down
    wheel_steer_cmd: f64, // wheel steering, -1.0~1.0
    wheel_brake_cmd: f64, // wheel brake, 0.0~1.0
}

impl Default for FlightControlCommand {
    fn default() -> FlightControlCommand {
        FlightControlCommand {
            power_cmd: vec![0.0],
            roll_cmd: 0.0,
            pitch_cmd: 0.0,
            yaw_cmd: 0.0,
            thrust_tilt_cmd: 0.0,
            flap_cmd: 0.0,
            speedbrake_cmd: 0.0,
            landing_gear_cmd: 0.0,
            wheel_steer_cmd: 0.0,
            wheel_brake_cmd: 0.0,
        }
    }
}

#[pymethods]
impl FlightControlCommand {
    #[new]
    #[pyo3(signature = (
        power_cmd=FlightControlCommand::default().power_cmd,
        roll_cmd=FlightControlCommand::default().roll_cmd,
        pitch_cmd=FlightControlCommand::default().pitch_cmd,
        yaw_cmd=FlightControlCommand::default().yaw_cmd,
        thrust_tilt_cmd=FlightControlCommand::default().thrust_tilt_cmd,
        flap_cmd=FlightControlCommand::default().flap_cmd,
        speedbrake_cmd=FlightControlCommand::default().speedbrake_cmd,
        landing_gear_cmd=FlightControlCommand::default().landing_gear_cmd,
        wheel_steer_cmd=FlightControlCommand::default().wheel_steer_cmd,
        wheel_brake_cmd=FlightControlCommand::default().wheel_brake_cmd))]
    pub fn new(
        power_cmd: Vec<f64>,
        roll_cmd: f64,
        pitch_cmd: f64,
        yaw_cmd: f64,
        thrust_tilt_cmd: f64,
        flap_cmd: f64,
        speedbrake_cmd: f64,
        landing_gear_cmd: f64,
        wheel_steer_cmd: f64,
        wheel_brake_cmd: f64,
    ) -> Self {
        FlightControlCommand {
            power_cmd,
            roll_cmd,
            pitch_cmd,
            yaw_cmd,
            thrust_tilt_cmd,
            flap_cmd,
            speedbrake_cmd,
            landing_gear_cmd,
            wheel_steer_cmd,
            wheel_brake_cmd,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("power_cmd", PyList::new(py, &self.power_cmd)?.as_ref())?;
        dict.set_item("roll_cmd", self.roll_cmd)?;
        dict.set_item("pitch_cmd", self.pitch_cmd)?;
        dict.set_item("yaw_cmd", self.yaw_cmd)?;
        dict.set_item("thrust_tilt_cmd", self.thrust_tilt_cmd)?;
        dict.set_item("flap_cmd", self.flap_cmd)?;
        dict.set_item("speedbrake_cmd", self.speedbrake_cmd)?;
        dict.set_item("landing_gear_cmd", self.landing_gear_cmd)?;
        dict.set_item("wheel_steer_cmd", self.wheel_steer_cmd)?;
        dict.set_item("wheel_brake_cmd", self.wheel_brake_cmd)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

// ----------------------------------------------------------------------------
// Aircraft Effector Command
// Output from flight controller, input to flight dynamics model

#[derive(Debug, Clone, Serialize, Deserialize, AerosimMessage, JsonSchema)]
#[pyclass(get_all, set_all)]
pub struct AircraftEffectorCommand {
    throttle_cmd: Vec<f64>,
    aileron_cmd_angle_rad: Vec<f64>,
    elevator_cmd_angle_rad: Vec<f64>,
    rudder_cmd_angle_rad: Vec<f64>,
    thrust_tilt_cmd_angle_rad: Vec<f64>,
    flap_cmd_angle_rad: Vec<f64>,
    speedbrake_cmd_angle_rad: Vec<f64>,
    landing_gear_cmd: Vec<f64>,
    wheel_steer_cmd_angle_rad: Vec<f64>,
    wheel_brake_cmd: Vec<f64>,
}

impl Default for AircraftEffectorCommand {
    fn default() -> AircraftEffectorCommand {
        AircraftEffectorCommand {
            throttle_cmd: vec![],
            aileron_cmd_angle_rad: vec![],
            elevator_cmd_angle_rad: vec![],
            rudder_cmd_angle_rad: vec![],
            thrust_tilt_cmd_angle_rad: vec![],
            flap_cmd_angle_rad: vec![],
            speedbrake_cmd_angle_rad: vec![],
            landing_gear_cmd: vec![],
            wheel_steer_cmd_angle_rad: vec![],
            wheel_brake_cmd: vec![],
        }
    }
}

#[pymethods]
impl AircraftEffectorCommand {
    #[new]
    #[pyo3(signature = (
        throttle_cmd=AircraftEffectorCommand::default().throttle_cmd,
        aileron_cmd_angle_rad=AircraftEffectorCommand::default().aileron_cmd_angle_rad,
        elevator_cmd_angle_rad=AircraftEffectorCommand::default().elevator_cmd_angle_rad,
        rudder_cmd_angle_rad=AircraftEffectorCommand::default().rudder_cmd_angle_rad,
        thrust_tilt_cmd_angle_rad=AircraftEffectorCommand::default().thrust_tilt_cmd_angle_rad,
        flap_cmd_angle_rad=AircraftEffectorCommand::default().flap_cmd_angle_rad,
        speedbrake_cmd_angle_rad=AircraftEffectorCommand::default().speedbrake_cmd_angle_rad,
        landing_gear_cmd=AircraftEffectorCommand::default().landing_gear_cmd,
        wheel_steer_cmd_angle_rad=AircraftEffectorCommand::default().wheel_steer_cmd_angle_rad,
        wheel_brake_cmd=AircraftEffectorCommand::default().wheel_brake_cmd
    ))]
    pub fn new(
        throttle_cmd: Vec<f64>,
        aileron_cmd_angle_rad: Vec<f64>,
        elevator_cmd_angle_rad: Vec<f64>,
        rudder_cmd_angle_rad: Vec<f64>,
        thrust_tilt_cmd_angle_rad: Vec<f64>,
        flap_cmd_angle_rad: Vec<f64>,
        speedbrake_cmd_angle_rad: Vec<f64>,
        landing_gear_cmd: Vec<f64>,
        wheel_steer_cmd_angle_rad: Vec<f64>,
        wheel_brake_cmd: Vec<f64>,
    ) -> Self {
        AircraftEffectorCommand {
            throttle_cmd,
            aileron_cmd_angle_rad,
            elevator_cmd_angle_rad,
            rudder_cmd_angle_rad,
            thrust_tilt_cmd_angle_rad,
            flap_cmd_angle_rad,
            speedbrake_cmd_angle_rad,
            landing_gear_cmd,
            wheel_steer_cmd_angle_rad,
            wheel_brake_cmd,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item(
            "throttle_cmd",
            PyList::new(py, &self.throttle_cmd)?.as_ref(),
        )?;
        dict.set_item(
            "aileron_cmd_angle_rad",
            PyList::new(py, &self.aileron_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "elevator_cmd_angle_rad",
            PyList::new(py, &self.elevator_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "rudder_cmd_angle_rad",
            PyList::new(py, &self.rudder_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "thrust_tilt_cmd_angle_rad",
            PyList::new(py, &self.thrust_tilt_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "flap_cmd_angle_rad",
            PyList::new(py, &self.flap_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "speedbrake_cmd_angle_rad",
            PyList::new(py, &self.speedbrake_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "landing_gear_cmd",
            PyList::new(py, &self.landing_gear_cmd)?.as_ref(),
        )?;
        dict.set_item(
            "wheel_steer_cmd_angle_rad",
            PyList::new(py, &self.wheel_steer_cmd_angle_rad)?.as_ref(),
        )?;
        dict.set_item(
            "wheel_brake_cmd",
            PyList::new(py, &self.wheel_brake_cmd)?.as_ref(),
        )?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
