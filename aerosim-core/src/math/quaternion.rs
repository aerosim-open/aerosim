pub use quaternion_core::RotationSequence;
pub use quaternion_core::RotationType;

#[derive(Clone, Copy, Debug)]
pub struct Quaternion {
    pub _quat: quaternion_core::Quaternion<f64>,
}

impl Quaternion {
    pub fn new(w: f64, x: f64, y: f64, z: f64) -> Self {
        let _quat: quaternion_core::Quaternion<f64> = (w, [x, y, z]);

        Self { _quat }
    }

    pub fn from_quaternion_data(quaternion_data: aerosim_data::types::Quaternion) -> Self {
        let _quat: quaternion_core::Quaternion<f64> = (
            quaternion_data.w,
            [quaternion_data.x, quaternion_data.y, quaternion_data.z],
        );

        Self { _quat }
    }

    pub fn from_euler_angles(
        angles: [f64; 3],
        rotation_type: RotationType,
        sequence: RotationSequence,
    ) -> Self {
        let _quat: quaternion_core::Quaternion<f64> =
            quaternion_core::from_euler_angles(rotation_type, sequence, angles);

        Self { _quat }
    }

    pub fn w(&self) -> f64 {
        self._quat.0
    }

    pub fn x(&self) -> f64 {
        self._quat.1[0]
    }

    pub fn y(&self) -> f64 {
        self._quat.1[1]
    }

    pub fn z(&self) -> f64 {
        self._quat.1[2]
    }

    pub fn to_euler_angles(
        &self,
        rotation_type: RotationType,
        sequence: RotationSequence,
    ) -> [f64; 3] {
        quaternion_core::to_euler_angles(rotation_type, sequence, self._quat)
    }

    pub fn dot(&self, other: Quaternion) -> f64 {
        self.w() * other.w() + self.x() * other.x() + self.y() * other.y() + self.z() * other.z()
    }

    pub fn normalize(&self) -> Quaternion {
        let magnitude =
            (self.w() * self.w() + self.x() * self.x() + self.y() * self.y() + self.z() * self.z())
                .sqrt();

        if magnitude == 0.0 {
            panic!("Cannot normalize a quaternion with zero magnitude");
        }
        let _quat: quaternion_core::Quaternion<f64> = (
            self.w() / magnitude,
            [
                self.x() / magnitude,
                self.y() / magnitude,
                self.z() / magnitude,
            ],
        );
        Quaternion { _quat }
    }
}
