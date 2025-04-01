use crate::Sensor;

#[pyclass(get_all, set_all)]
#[derive(Clone, Copy, Debug)]
pub struct Vector3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Default for Vector3 {
    fn default() -> Self {
        Self {
            x: 0.0,
            y: 0.0,
            z: 0.0,
        }
    }
}

#[pymethods]
impl Vector3 {
    #[new]
    #[pyo3(signature = (x = 0.0, y = 0.0, z = 0.0))]
    pub fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    pub const fn to_python_tuple(&self) -> (f64, f64, f64) {
        (self.x, self.y, self.z)
    }
}

use pyo3::{prelude::*, types::PyDict};
#[pyclass(extends=Sensor, get_all, set_all)]
#[derive(Clone, Copy, Debug)]
pub struct GNSS {
    pub latitude: f64,     // Latitude in decimal degrees
    pub longitude: f64,    // Longitude in decimal degrees
    pub altitude: f64,     // Altitude in meters above mean sea level
    pub velocity: Vector3, // Velocity in the north, east and downward directions (m/s)
    pub heading: f64,      // Heading or course over ground in degrees
    pub timestamp: f64,    // Timestamp of the data in seconds since epoch
    pub prev_velocity: Option<Vector3>,
    pub prev_timestamp: Option<f64>,
}

const EQUATORIAL_EARTH_RADIUS: f64 = 6_378_137.0;
const POLAR_EARTH_RADIUS: f64 = 6_356_752.314_245;
const EARTH_FLATTENING: f64 =
    (EQUATORIAL_EARTH_RADIUS - POLAR_EARTH_RADIUS) / EQUATORIAL_EARTH_RADIUS;

#[pymethods]
impl GNSS {
    #[new]
    #[pyo3(signature = (latitude, longitude, altitude, velocity_n=0.0, velocity_e=0.0, velocity_d=0.0, heading=0.0, timestamp=0.0))]
    fn new(
        latitude: f64,
        longitude: f64,
        altitude: f64,
        velocity_n: f64,
        velocity_e: f64,
        velocity_d: f64,
        heading: f64,
        timestamp: f64,
    ) -> (Self, Sensor) {
        let velocity = Vector3::new(velocity_n, velocity_e, velocity_d);
        (
            Self {
                latitude,
                longitude,
                altitude,
                velocity,
                heading,
                timestamp,
                prev_velocity: None,
                prev_timestamp: None,
            },
            Sensor::new("GNSS".to_string(), 0.0),
        )
    }

    fn translate(&mut self, x: f64, y: f64, z: f64) {
        let mut mercator = self.to_mercator();
        mercator.0 += x;
        mercator.1 += y;

        self.from_mercator(mercator.0, mercator.1, z);
    }

    fn calculate_distance(&self, other: &Self) -> Option<f64> {
        let delta_lon = (other.longitude - self.longitude).to_radians();
        let u1 = ((1.0 - EARTH_FLATTENING) * self.latitude.to_radians().tan()).atan();
        let u2 = ((1.0 - EARTH_FLATTENING) * other.latitude.to_radians().tan()).atan();
        let (sin_u1, cos_u1) = u1.sin_cos();
        let (sin_u2, cos_u2) = u2.sin_cos();

        let mut cos_sq_alpha;
        let mut sin_sigma;
        let mut cos2_sigma_m;
        let mut cos_sigma;
        let mut sigma;

        let mut lambda = delta_lon;
        let mut lambda_p;
        let mut iter_limit = 100;

        loop {
            let (sin_lambda, cos_lambda) = lambda.sin_cos();
            sin_sigma = ((cos_u2 * sin_lambda) * (cos_u2 * sin_lambda)
                + (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda)
                    * (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda))
                .sqrt();
            if sin_sigma.abs() < 1e-6 {
                return if self.longitude == other.longitude && self.latitude == other.latitude {
                    Some(0.0)
                } else {
                    None
                };
            }
            cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda;
            sigma = sin_sigma.atan2(cos_sigma);
            let sin_alpha = cos_u1 * cos_u2 * sin_lambda / sin_sigma;
            cos_sq_alpha = 1.0 - sin_alpha * sin_alpha;

            if cos_sq_alpha.abs() < 1e-6 {
                cos2_sigma_m = 0.0
            } else {
                cos2_sigma_m = cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha;
            }

            let c = EARTH_FLATTENING / 16.0
                * cos_sq_alpha
                * (4.0 + EARTH_FLATTENING * (4.0 - 3.0 * cos_sq_alpha));
            lambda_p = lambda;
            lambda = delta_lon
                + (1.0 - c)
                    * EARTH_FLATTENING
                    * sin_alpha
                    * (sigma
                        + c * sin_sigma
                            * (cos2_sigma_m
                                + c * cos_sigma * (-1.0 + 2.0 * cos2_sigma_m * cos2_sigma_m)));

            if (lambda - lambda_p).abs() <= 1e-12 {
                break;
            }
            iter_limit -= 1;
            if iter_limit == 0 {
                break;
            }
        }

        if iter_limit == 0 {
            return None;
        }

        let u_sq = cos_sq_alpha
            * (EQUATORIAL_EARTH_RADIUS * EQUATORIAL_EARTH_RADIUS
                - POLAR_EARTH_RADIUS * POLAR_EARTH_RADIUS)
            / (POLAR_EARTH_RADIUS * POLAR_EARTH_RADIUS);
        let a = 1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)));
        let b = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)));
        let delta_sigma = b
            * sin_sigma
            * (cos2_sigma_m
                + b / 4.0
                    * (cos_sigma * (-1.0 + 2.0 * cos2_sigma_m * cos2_sigma_m)
                        - b / 6.0
                            * cos2_sigma_m
                            * (-3.0 + 4.0 * sin_sigma * sin_sigma)
                            * (-3.0 + 4.0 * cos2_sigma_m * cos2_sigma_m)));
        Some(POLAR_EARTH_RADIUS * a * (sigma - delta_sigma))
    }

    fn to_mercator(&self) -> (f64, f64) {
        let x = EQUATORIAL_EARTH_RADIUS * self.longitude.to_radians();
        let y = EQUATORIAL_EARTH_RADIUS
            * (std::f64::consts::FRAC_PI_4 + self.latitude.to_radians() / 2.0)
                .tan()
                .ln();
        (x, y)
    }

    fn to_ned(&self, target: &Self) -> (f64, f64, f64) {
        let ref_ecef = self.to_ecef();
        let target_ecef = target.to_ecef();
        self.ecef_to_ned(target_ecef, ref_ecef, self.latitude, self.longitude)
    }

    fn to_ecef(&self) -> (f64, f64, f64) {
        let lat_rad = self.latitude.to_radians();
        let lon_rad = self.longitude.to_radians();

        let sin_lat = lat_rad.sin();
        let cos_lat = lat_rad.cos();
        let cos_lon = lon_rad.cos();
        let sin_lon = lon_rad.sin();

        let n = EQUATORIAL_EARTH_RADIUS
            / (1.0 - EARTH_FLATTENING * (2.0 - EARTH_FLATTENING) * sin_lat.powi(2)).sqrt();
        let x = (n + self.altitude) * cos_lat * cos_lon;
        let y = (n + self.altitude) * cos_lat * sin_lon;
        let z = (n * (1.0 - EARTH_FLATTENING).powi(2) + self.altitude) * sin_lat;

        (x, y, z)
    }

    fn ecef_to_ned(
        &self,
        target_ecef: (f64, f64, f64),
        ref_ecef: (f64, f64, f64),
        ref_lat: f64,
        ref_lon: f64,
    ) -> (f64, f64, f64) {
        let (dx, dy, dz) = (
            target_ecef.0 - ref_ecef.0,
            target_ecef.1 - ref_ecef.1,
            target_ecef.2 - ref_ecef.2,
        );

        let lat_rad = ref_lat.to_radians();
        let lon_rad = ref_lon.to_radians();

        let sin_lat = lat_rad.sin();
        let cos_lat = lat_rad.cos();
        let sin_lon = lon_rad.sin();
        let cos_lon = lon_rad.cos();

        let ned_north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz;
        let ned_east = -sin_lon * dx + cos_lon * dy;
        let ned_down = -cos_lat * cos_lon * dx - cos_lat * sin_lon * dy - sin_lat * dz;

        (ned_north, ned_east, ned_down)
    }

    #[getter(velocity)]
    fn get_velocity(&self) -> PyResult<(f64, f64, f64)> {
        Ok(self.velocity.to_python_tuple())
    }

    #[setter(velocity)]
    fn set_velocity(&mut self, velocity: (f64, f64, f64)) -> PyResult<()> {
        self.velocity = Vector3::new(velocity.0, velocity.1, velocity.2);
        Ok(())
    }

    #[pyo3(signature = (x, y, z=0.0))]
    fn from_mercator(&mut self, x: f64, y: f64, z: f64) {
        self.longitude = x / EQUATORIAL_EARTH_RADIUS * 180.0 / std::f64::consts::PI;
        self.latitude = (2.0 * (y / EQUATORIAL_EARTH_RADIUS).exp().atan()
            - std::f64::consts::FRAC_PI_2)
            * 180.0
            / std::f64::consts::PI;
        self.altitude = z;
    }

    pub fn update(
        &mut self,
        latitude: f64,
        longitude: f64,
        altitude: f64,
        velocity_n: f64,
        velocity_e: f64,
        velocity_d: f64,
        heading: f64,
        timestamp: f64,
    ) {
        self.prev_velocity = Some(self.velocity);
        self.prev_timestamp = Some(self.timestamp);

        self.latitude = latitude;
        self.longitude = longitude;
        self.altitude = altitude;
        self.velocity = Vector3::new(velocity_n, velocity_e, velocity_d);
        self.heading = heading;
        self.timestamp = timestamp;
    }

    pub fn get_acceleration(&self) -> PyResult<(f64, f64, f64)> {
        if self.prev_velocity.is_none() || self.prev_timestamp.is_none() {
            return Ok((0.0, 0.0, 0.0));
        }

        let prev_velocity = self.prev_velocity.unwrap_or_default();
        let prev_timestamp = self.prev_timestamp.unwrap_or_default();

        let dt = self.timestamp - prev_timestamp;
        if dt <= f64::EPSILON {
            return Ok((0.0, 0.0, 0.0));
        }

        let acceleration = Vector3::new(
            (self.velocity.x - prev_velocity.x) / dt,
            (self.velocity.y - prev_velocity.y) / dt,
            (self.velocity.z - prev_velocity.z) / dt,
        );

        Ok(acceleration.to_python_tuple())
    }

    pub fn get_ground_speed(&self) -> f64 {
        (self.velocity.x.powi(2) + self.velocity.y.powi(2)).sqrt()
    }

    pub fn compute_velocity(&self) -> f64 {
        (self.velocity.x.powi(2) + self.velocity.y.powi(2) + self.velocity.z.powi(2)).sqrt()
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let _ = dict.set_item("latitude", self.latitude)?;
        let _ = dict.set_item("longitude", self.longitude)?;
        let _ = dict.set_item("altitude", self.altitude)?;
        let _ = dict.set_item("velocity", self.velocity.to_python_tuple())?;
        let _ = dict.set_item("heading", self.heading)?;
        Ok(dict.into())
    }

    pub fn __dict__(&self, py: Python) -> PyResult<PyObject> {
        self.to_dict(py)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gnss_to_mercator() {
        let ny_longitude = -73.935242;
        let ny_latitude = 40.730610;
        let (gnss, _) = GNSS::new(ny_latitude, ny_longitude, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);

        let expected_x = -8230433.491117454;
        let expected_y = 4972687.535733602;
        let mercator = gnss.to_mercator();

        let delta_error = 1e-9;
        assert!(
            mercator.0 - expected_x < delta_error,
            "Error: got x = {}, expected = {}, delta = {}",
            mercator.0,
            expected_x,
            mercator.0 - expected_x
        );
        assert!(
            mercator.1 - expected_y < delta_error,
            "Error: got y = {}, expected = {}, delta = {}",
            mercator.1,
            expected_y,
            mercator.1 - expected_y
        );
    }

    #[test]
    fn test_mercator_to_gnss() {
        let expected_longitude = -73.935242;
        let expected_latitude = 40.730610;
        let (mut gnss, _) = GNSS::new(
            expected_latitude,
            expected_longitude,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        );

        let (x, y) = gnss.to_mercator();
        gnss.from_mercator(x, y, 0.0);

        let delta_error = 1e-9;
        assert!(
            gnss.longitude - expected_longitude < delta_error,
            "Error: got x = {}, expected = {}, delta = {}",
            gnss.longitude,
            expected_longitude,
            gnss.longitude - expected_longitude
        );
        assert!(
            gnss.latitude - expected_latitude < delta_error,
            "Error: got y = {}, expected = {}, delta = {}",
            gnss.latitude,
            expected_latitude,
            gnss.latitude - expected_latitude
        );
    }

    #[test]
    fn test_calculate_distance() {
        let la_longitude = -118.243683;
        let la_latitude = 34.052235;
        let (la, _) = GNSS::new(la_latitude, la_longitude, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);

        let ny_longitude = -73.935242;
        let ny_latitude = 40.730610;

        let (ny, _) = GNSS::new(ny_latitude, ny_longitude, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);

        let expected_distance = 3_950_255.654_154_592_7;
        let distance = la.calculate_distance(&ny).unwrap();
        let delta_error = 1e-3;
        let result = (distance - expected_distance).abs();
        assert!(
            result < delta_error,
            "Error: got distance = {}, expected = {}, delta = {} meters",
            distance,
            expected_distance,
            result
        );
    }

    #[test]
    fn test_gnss_ned_1() {
        let (reference, _) = GNSS::new(37.6194495, -122.3767776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
        let (target, _) = GNSS::new(37.6194495, -122.3767776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);

        let (n, e, d) = reference.to_ned(&target);
        let expected_n = 0.0;
        let expected_e = 0.0;
        let expected_d = 0.0;
        let delta_error = 1e-3;
        let delta_n = (n - expected_n).abs();
        let delta_e = (e - expected_e).abs();
        let delta_d = (d - expected_d).abs();

        assert!(
            delta_n < delta_error,
            "Error: n = {}, expected = {}, delta = {} meters",
            n,
            expected_n,
            delta_n
        );
        assert!(
            delta_e < delta_error,
            "Error: e = {}, expected = {}, delta = {} meters",
            e,
            expected_e,
            delta_e
        );
        assert!(
            delta_d < delta_error,
            "Error: d = {}, expected = {}, delta = {} meters",
            d,
            expected_d,
            delta_d
        );
    }

    #[test]
    fn test_gnss_ned_2() {
        let (reference, _) = GNSS::new(37.6194495, -122.3767776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
        let (target, _) = GNSS::new(37.6420439, -122.4094735, 304.8, 0.0, 0.0, 0.0, 0.0, 0.0);

        let (n, e, d) = reference.to_ned(&target);
        let expected_n = 2_508.363_922_893_28;
        let expected_e = -2_885.801_523_071_885_6;
        let expected_d = -303.653_321_176_709_3;
        let delta_error = 1e-3;
        let delta_n = (n - expected_n).abs();
        let delta_e = (e - expected_e).abs();
        let delta_d = (d - expected_d).abs();

        assert!(
            delta_n < delta_error,
            "Error: n = {}, expected = {}, delta = {} meters",
            n,
            expected_n,
            delta_n
        );
        assert!(
            delta_e < delta_error,
            "Error: e = {}, expected = {}, delta = {} meters",
            e,
            expected_e,
            delta_e
        );
        assert!(
            delta_d < delta_error,
            "Error: d = {}, expected = {}, delta = {} meters",
            d,
            expected_d,
            delta_d
        );
    }

    #[test]
    fn test_gnss_ned_3() {
        let (reference, _) = GNSS::new(37.6194495, -122.3767776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
        let (target, _) = GNSS::new(37.6481151, -122.4247364, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);

        let (n, e, d) = reference.to_ned(&target);
        let expected_n = 3_182.663_395_732_058;
        let expected_e = -4_232.386_955_261_773;
        let expected_d = 2.198_932_524_063_9;
        let delta_error = 1e-3;
        let delta_n = (n - expected_n).abs();
        let delta_e = (e - expected_e).abs();
        let delta_d = (d - expected_d).abs();

        assert!(
            delta_n < delta_error,
            "Error: n = {}, expected = {}, delta = {} meters",
            n,
            expected_n,
            delta_n
        );
        assert!(
            delta_e < delta_error,
            "Error: e = {}, expected = {}, delta = {} meters",
            e,
            expected_e,
            delta_e
        );
        assert!(
            delta_d < delta_error,
            "Error: d = {}, expected = {}, delta = {} meters",
            d,
            expected_d,
            delta_d
        );
    }

    #[test]
    fn test_translate() {
        let (mut sensor, _) = GNSS::new(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
        sensor.translate(1000.0, 500.0, 0.0);

        let expected_latitude = 0.004491576415997162;
        let expected_longitude = 0.008983152841195215;

        let delta_error = 1e-6;
        let latitude_result = (sensor.latitude - expected_latitude).abs();
        let longitude_result = (sensor.longitude - expected_longitude).abs();

        assert!(
            longitude_result < delta_error,
            "Error: Longitude was = {}, expected = {}, delta = {}",
            sensor.longitude,
            expected_longitude,
            longitude_result
        );
        assert!(
            latitude_result < delta_error,
            "Error: Latitude was = {}, expected = {}, delta = {}",
            sensor.latitude,
            expected_latitude,
            latitude_result
        );
    }
}
