use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use strum_macros::{Display, EnumString};

// Main Schema for Scenarios
#[pyclass(get_all, set_all)]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Scenario {
    pub scenario_id: String,
    pub description: String,
    pub time_of_day: String,
    pub latitude: f32,
    pub longitude: f32,
    pub height: f32,
    pub weather: Vec<WeatherScenarioData>,
    pub cesium_height_offset_map: String,
    pub actors: Vec<ActorScenarioData>,
    pub trajectories: Vec<TrajectoryScenarioData>,
    pub sensor_setup: Vec<SensorScenarioData>,
}

#[pyclass(get_all, set_all)]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct WeatherScenarioData {
    pub weather_id: String,
    pub config_file: String,
}

#[pyclass(get_all, set_all)]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ActorScenarioData {
    pub actor_id: String,
    pub actor_type: String,
    pub latitude: f64,
    pub longitude: f64,
    pub height: f64,
    pub config_file: String,
    pub id: Option<String>,
    pub usd: Option<String>,
    pub description: Option<String>,
    pub transform: Option<Transform>,
    pub state: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ActorAuxiliarScenarioData {
    pub id: String,
    pub usd: String,
    pub description: String,
    pub transform: Option<Transform>,
    pub state: Option<String>,
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Transform {
    #[pyo3(get, set)]
    pub translation: [f64; 3], // Translation as [x, y, z]

    pub rotation: Rotation, // Euler angles or Quaternion

    #[pyo3(get, set)]
    pub scale: Option<[f64; 3]>, // Scale as [x, y, z]
}

// Enum for rotation to support both Euler angles and Quaternion
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(untagged)]
pub enum Rotation {
    Euler([f64; 3]),      // [roll, pitch, yaw]
    Quaternion([f64; 4]), // [x, y, z, w]
}

impl Rotation {
    pub fn to_euler_vec(&self) -> Vec<f64> {
        match self {
            // If it's already Euler, return as Vec
            Rotation::Euler(euler) => euler.to_vec(),

            // Convert Quaternion to Euler angles
            Rotation::Quaternion(quat) => {
                let [x, y, z, w] = quat;
                let roll = (2.0 * (w * x + y * z)).atan2(1.0 - 2.0 * (x * x + y * y));
                let pitch = (2.0 * (w * y - z * x)).asin();
                let yaw = (2.0 * (w * z + x * y)).atan2(1.0 - 2.0 * (y * y + z * z));
                vec![roll, pitch, yaw]
            }
        }
    }
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct TrajectoryScenarioData {
    #[pyo3(get, set)]
    pub trajectory_id: String,
    #[pyo3(get, set)]
    pub object_id: String,
    #[pyo3(get, set)]
    pub config_file: String,
    #[pyo3(get, set)]
    pub trajectory: Option<Vec<Waypoints>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct TrajectoryAuxScenarioData {
    pub trajectory: Vec<Waypoints>,
}

#[pyclass(get_all, set_all)]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Waypoints {
    pub timestamp: f64, // Timestamp of the checkpoint in seconds format
    pub latitude: f64,  // Latitude in decimal degrees (-90 to 90)
    pub longitude: f64, // Longitude in decimal degrees (-180 to 180)
    pub height: f64,    // Height in meters above sea level
}

#[pymethods]
impl Waypoints {
    #[new]
    pub fn new(timestamp: f64, latitude: f64, longitude: f64, height: f64) -> Self {
        Waypoints {
            timestamp,
            latitude,
            longitude,
            height,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyObject {
        let dict = PyDict::new(py);
        dict.set_item("time", self.timestamp).unwrap();
        dict.set_item("lat", self.latitude).unwrap();
        dict.set_item("lon", self.longitude).unwrap();
        dict.set_item("alt", self.height).unwrap();
        dict.into()
    }
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SensorScenarioData {
    #[pyo3(get, set)]
    pub sensor_name: String,
    #[pyo3(get, set)]
    pub vehicle: String,
    #[pyo3(get, set)]
    pub config_file: String,
    #[pyo3(get, set)]
    pub id: Option<String>, // Unique identifier for the sensor
    #[pyo3(get, set)]
    pub sensor_type: Option<SensorType>, // Type of the sensor (enum)
    #[pyo3(get, set)]
    pub relative_transform: Option<Transform>, // Relative transformation of the sensor

    pub parameters: Option<SensorParameters>, // Specific configuration parameters for the sensor
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SensorScenarioAuxData {
    pub id: Option<String>,                    // Unique identifier for the sensor
    pub sensor_type: Option<SensorType>,       // Type of the sensor (enum)
    pub relative_transform: Option<Transform>, // Relative transformation of the sensor
    pub parameters: Option<SensorParameters>,  // Specific configuration parameters for the sensor
}

#[pyclass(eq, eq_int)]
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Eq, EnumString, Display)]
pub enum SensorType {
    Lidar,
    Rgbcamera,
    Adsb,
    MultiCamera,
}
#[pymethods]
impl SensorType {
    #[staticmethod]
    pub fn from_str(s: &str) -> PyResult<Self> {
        s.parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid SensorType"))
    }

    pub fn __str__(&self) -> String {
        self.to_string()
    }

    pub fn __repr__(&self) -> String {
        format!("SensorType::{}", self)
    }

    #[staticmethod]
    pub fn to_dict(py: Python) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        for variant in [
            SensorType::Lidar,
            SensorType::Rgbcamera,
            SensorType::Adsb,
            SensorType::MultiCamera,
        ] {
            dict.set_item(variant.to_string(), variant.__repr__())?;
        }
        Ok(dict.into())
    }
}

// SensorParameters enum (placeholder for actual definitions)
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(untagged)]
pub enum SensorParameters {
    ADSB(ADSBParameters),
    Lidar(LidarParameters),
    Rgbcamera(RGBCameraParameters),
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ADSBParameters {
    #[pyo3(get, set)]
    pub frequency: f64, // Operating frequency in MHz

    #[pyo3(get, set)]
    pub range: f64, // Detection range in kilometers

    #[pyo3(get, set)]
    pub data_rate: f64, // Data rate in kbps
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct LidarParameters {
    #[pyo3(get, set)]
    pub range: f64, // Maximum range in meters

    #[pyo3(get, set)]
    pub field_of_view: f64, // Field of view in degrees

    #[pyo3(get, set)]
    pub rotation_rate: f64, // Rotation rate in Hz

    #[pyo3(get, set)]
    pub point_density: Option<f64>, // Density of points per second in millions (optional)
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct RGBCameraParameters {
    #[pyo3(get, set)]
    pub resolution: [u32; 2], // Resolution [width, height]

    #[pyo3(get, set)]
    pub frame_rate: f64, // Frame rate in FPS

    #[pyo3(get, set)]
    pub field_of_view: f64, // Field of view in degrees
}

// JSON Reader and Writer
#[pyfunction]
pub fn read_scenario_json(file_path: &str) -> PyResult<Scenario> {
    let mut file =
        File::open(file_path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    // Determine the file's parent directory
    let file_struct_path = Path::new(file_path).parent().ok_or_else(|| {
        pyo3::exceptions::PyValueError::new_err("Failed to determine parent directory")
    })?;

    let mut contents = String::new();
    file.read_to_string(&mut contents)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let mut data: Scenario = serde_json::from_str(&contents)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    for actor in data.actors.iter_mut() {
        let actor_config_path: PathBuf = file_struct_path.join(&actor.config_file);

        let mut aux_file = File::open(&actor_config_path).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to open actor config file {}: {}",
                actor_config_path.display(),
                e
            ))
        })?;

        let mut auxcontents = String::new();
        aux_file.read_to_string(&mut auxcontents).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to read config file {}: {}",
                actor_config_path.display(),
                e
            ))
        })?;
        let auxdata: ActorAuxiliarScenarioData =
            serde_json::from_str(&auxcontents).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Failed to parse actor config JSON from {}: {}",
                    actor_config_path.display(),
                    e
                ))
            })?;
        actor.id = Some(auxdata.id);
        actor.usd = Some(auxdata.usd);
        actor.description = Some(auxdata.description);
        actor.state = auxdata.state;
        actor.transform = auxdata.transform;
    }
    for trajectory in data.trajectories.iter_mut() {
        let trayectory_config_path: PathBuf = file_struct_path.join(&trajectory.config_file);

        let mut aux_file = File::open(&trayectory_config_path).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to open trajectory config file {}: {}",
                trayectory_config_path.display(),
                e
            ))
        })?;

        let mut auxcontents = String::new();
        aux_file.read_to_string(&mut auxcontents).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to read trajectory config file {}: {}",
                trayectory_config_path.display(),
                e
            ))
        })?;
        let auxdata: TrajectoryAuxScenarioData =
            serde_json::from_str(&auxcontents).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Failed to parse trajectory config JSON from {}: {}",
                    trayectory_config_path.display(),
                    e
                ))
            })?;
        trajectory.trajectory = Some(auxdata.trajectory);
    }
    for sensor in data.sensor_setup.iter_mut() {
        let sensor_config_path: PathBuf = file_struct_path.join(&sensor.config_file);

        let mut aux_file = File::open(&sensor_config_path).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to open sensor config file {}: {}",
                sensor_config_path.display(),
                e
            ))
        })?;

        let mut auxcontents = String::new();
        aux_file.read_to_string(&mut auxcontents).map_err(|e| {
            pyo3::exceptions::PyIOError::new_err(format!(
                "Failed to read sensor config file {}: {}",
                sensor_config_path.display(),
                e
            ))
        })?;
        let auxdata: SensorScenarioAuxData = serde_json::from_str(&auxcontents).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "Failed to parse sensor config JSON from {}: {}",
                sensor_config_path.display(),
                e
            ))
        })?;
        sensor.id = auxdata.id;
        sensor.sensor_type = auxdata.sensor_type;
        sensor.relative_transform = auxdata.relative_transform;
        sensor.parameters = auxdata.parameters;
    }
    Ok(data)
}

#[pyfunction]
pub fn write_scenario_json(file_path: &str, data: Scenario) -> PyResult<()> {
    let json = serde_json::to_string_pretty(&data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let mut file =
        File::create(file_path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    file.write_all(json.as_bytes())
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    Ok(())
}
