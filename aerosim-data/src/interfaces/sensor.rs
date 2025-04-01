use crate::types::SensorType;
pub trait Sensor {
    type SensorDataType;

    fn get_sensor_type(&self) -> SensorType;
    fn get_data(&self) -> Self::SensorDataType;
}

use crate::types::{ActorModel, ActorState, Image, Vector3};

pub struct CameraSensor {
    pub uid: u64,
    pub model: ActorModel,
    pub state: ActorState,
    pub data: Image,
}

impl Sensor for CameraSensor {
    type SensorDataType = Image;

    fn get_sensor_type(&self) -> SensorType {
        SensorType::Camera
    }
    fn get_data(&self) -> Self::SensorDataType {
        self.data.clone()
    }
}

pub struct LidarSensor {
    pub uid: u64,
    pub model: ActorModel,
    pub state: ActorState,
    pub data: Vec<Vector3>, // Assume Lidar returns point cloud data
}

impl Sensor for LidarSensor {
    type SensorDataType = Vec<Vector3>;

    fn get_sensor_type(&self) -> SensorType {
        SensorType::LIDAR
    }
    fn get_data(&self) -> Self::SensorDataType {
        self.data.clone()
    }
}
