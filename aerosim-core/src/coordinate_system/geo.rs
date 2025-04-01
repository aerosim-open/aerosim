use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use std::fs::File;
use std::io::Read;

#[pyclass(get_all)]
#[derive(Copy, Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Ellipsoid {
    pub equatorial_radius: f64,
    pub flattening_factor: f64,
    pub polar_radius: f64,
}

#[pymethods]
impl Ellipsoid {
    #[staticmethod]
    pub fn wgs84() -> Self {
        let equatorial_radius = 6378137.0;
        let flattening_factor = 1.0 / 298.257223563;
        let polar_radius = equatorial_radius * (1.0 - flattening_factor);
        Self {
            equatorial_radius,
            flattening_factor,
            polar_radius,
        }
    }

    #[staticmethod]
    #[pyo3(signature = (equatorial_radius = 0.0, flattening_factor = 0.0))]
    pub fn custom(equatorial_radius: f64, flattening_factor: f64) -> Self {
        let polar_radius = equatorial_radius * (1.0 - flattening_factor);
        Self {
            equatorial_radius,
            flattening_factor,
            polar_radius,
        }
    }
}

pub trait GeoidModel: Send + Sync {
    fn geoid_height(&self, lat: f64, lon: f64) -> f64;
}

#[pyclass]
#[derive(Copy, Clone, Debug)]
pub struct EGM08;

impl GeoidModel for EGM08 {
    fn geoid_height(&self, lat: f64, lon: f64) -> f64 {
        // The egm2008 crate's geoid_height() takes parameters as f32 because
        // internally it uses f32 precision. If higher lat/lon precision is needed,
        // may need to look for another geoid model dependency.
        egm2008::geoid_height(lat as f32, lon as f32)
            .map(|height| height as f64)
            .unwrap_or(f64::NAN)
    }
}

#[pyclass]
pub struct Geoid {
    model: Box<dyn GeoidModel>,
}

#[pymethods]
impl Geoid {
    #[staticmethod]
    pub fn egm08() -> Self {
        Self {
            model: Box::new(EGM08),
        }
    }

    // Method to get geoid height given latitude and longitude
    pub fn get_geoid_height(&self, lat: f64, lon: f64) -> f64 {
        self.model.geoid_height(lat, lon)
    }
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct GeodeticBounds {
    pub lat_min: f64,
    pub lat_max: f64,
    pub lon_min: f64,
    pub lon_max: f64,
}

#[pymethods]
impl GeodeticBounds {
    #[new]
    pub fn new(lat_min: f64, lat_max: f64, lon_min: f64, lon_max: f64) -> Self {
        GeodeticBounds {
            lat_min,
            lat_max,
            lon_min,
            lon_max,
        }
    }
}

#[pyclass]
#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct OffsetMap {
    pub bounds: GeodeticBounds,
    pub lat_resolution: usize,
    pub lon_resolution: usize,
    pub offsets: Vec<f64>,
}

#[pymethods]
impl OffsetMap {
    #[new]
    pub fn new(
        bounds: GeodeticBounds,
        lat_resolution: usize,
        lon_resolution: usize,
        offsets: Vec<f64>,
    ) -> Self {
        assert_eq!(offsets.len(), lat_resolution * lon_resolution);

        OffsetMap {
            bounds,
            lat_resolution,
            lon_resolution,
            offsets,
        }
    }

    #[staticmethod]
    pub fn from_json(file_path: &str) -> Self {
        let mut file = File::open(file_path).expect("Unable to open file");
        let mut data = String::new();
        file.read_to_string(&mut data).expect("Unable to read file");

        let json_data: serde_json::Value =
            serde_json::from_str(&data).expect("Unable to parse JSON");

        let bounds = json_data["bounds"].clone();
        let lat_min = bounds["lat_min"]
            .as_f64()
            .expect("lat_min should be a float");
        let lat_max = bounds["lat_max"]
            .as_f64()
            .expect("lat_max should be a float");
        let lon_min = bounds["lon_min"]
            .as_f64()
            .expect("lon_min should be a float");
        let lon_max = bounds["lon_max"]
            .as_f64()
            .expect("lon_max should be a float");

        let lat_resolution = json_data["lat_resolution"]
            .as_u64()
            .expect("lat_resolution should be an integer") as usize;
        let lon_resolution = json_data["lon_resolution"]
            .as_u64()
            .expect("lon_resolution should be an integer") as usize;

        let offsets = json_data["offsets"]
            .as_array()
            .expect("offsets should be an array")
            .iter()
            .map(|v| v.as_f64().expect("offset should be a float"))
            .collect();

        OffsetMap {
            bounds: GeodeticBounds {
                lat_min,
                lat_max,
                lon_min,
                lon_max,
            },
            lat_resolution,
            lon_resolution,
            offsets,
        }
    }

    //Using bilinear interpolation
    pub fn get_offset(&self, lat: f64, lon: f64) -> f64 {
        //Clamp the latitude and longitude to the bounds so we don't go out of bounds, this means if we query a point outside of bounds we will get the value at the edge of the interpolated region
        let lat_bounded = lat.clamp(self.bounds.lat_min, self.bounds.lat_max);
        let lon_bounded = lon.clamp(self.bounds.lon_min, self.bounds.lon_max);

        let lat_step =
            (self.bounds.lat_max - self.bounds.lat_min) / ((self.lat_resolution - 1) as f64);
        let lon_step =
            (self.bounds.lon_max - self.bounds.lon_min) / ((self.lon_resolution - 1) as f64);

        //Find the indices of the 4 points we need to interpolate between
        let lat_floor_index = (((lat_bounded - self.bounds.lat_min) / lat_step).floor() as usize)
            .min(self.lat_resolution - 2);
        let lon_floor_index = (((lon_bounded - self.bounds.lon_min) / lon_step).floor() as usize)
            .min(self.lon_resolution - 2);

        let lat_ceil_index = lat_floor_index + 1;
        let lon_ceil_index = lon_floor_index + 1;

        //Find the values of the 4 points we need to interpolate between
        let f_11 = self.offsets[lon_floor_index * self.lat_resolution + lat_floor_index];
        let f_12 = self.offsets[lon_ceil_index * self.lat_resolution + lat_floor_index];
        let f_21 = self.offsets[lon_floor_index * self.lat_resolution + lat_ceil_index];
        let f_22 = self.offsets[lon_ceil_index * self.lat_resolution + lat_ceil_index];

        //Find the values of the 4 points we need to interpolate between
        let lat_floor = self.bounds.lat_min + lat_floor_index as f64 * lat_step;
        let lat_ceil = self.bounds.lat_min + lat_ceil_index as f64 * lat_step;
        let lon_floor = self.bounds.lon_min + lon_floor_index as f64 * lon_step;
        let lon_ceil = self.bounds.lon_min + lon_ceil_index as f64 * lon_step;

        //Calculate the weights for the interpolation
        let w_11 = (lat_ceil - lat_bounded) * (lon_ceil - lon_bounded)
            / ((lat_ceil - lat_floor) * (lon_ceil - lon_floor));
        let w_12 = (lat_ceil - lat_bounded) * (lon_bounded - lon_floor)
            / ((lat_ceil - lat_floor) * (lon_ceil - lon_floor));
        let w_21 = (lat_bounded - lat_floor) * (lon_ceil - lon_bounded)
            / ((lat_ceil - lat_floor) * (lon_ceil - lon_floor));
        let w_22 = (lat_bounded - lat_floor) * (lon_bounded - lon_floor)
            / ((lat_ceil - lat_floor) * (lon_ceil - lon_floor));

        //Interpolate the value
        let offset = w_11 * f_11 + w_12 * f_12 + w_21 * f_21 + w_22 * f_22;
        offset
    }
}

#[pyfunction]
// Haversine distance in meters from (lat1, lon1) to (lat2, lon2)
pub fn haversine_distance_meters(
    lat1_deg: f64,
    lon1_deg: f64,
    lat2_deg: f64,
    lon2_deg: f64,
) -> PyResult<f64> {
    let r = 6371.0; // Earth radius in km
    let d_lat = (lat2_deg - lat1_deg).to_radians();
    let d_lon = (lon2_deg - lon1_deg).to_radians();
    let a = (d_lat / 2.0).sin() * (d_lat / 2.0).sin()
        + lat1_deg.to_radians().cos()
            * lat2_deg.to_radians().cos()
            * (d_lon / 2.0).sin()
            * (d_lon / 2.0).sin();
    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    Ok(r * c * 1000.0) // return distance in meters
}

// Bearing angle in degrees (0-360) for line from (lat1, lon1) to (lat2, lon2)
#[pyfunction]
pub fn bearing_deg(lat1_deg: f64, lon1_deg: f64, lat2_deg: f64, lon2_deg: f64) -> PyResult<f64> {
    let lat1_rad = lat1_deg.to_radians();
    let lat2_rad = lat2_deg.to_radians();
    let delta_lon = (lon2_deg - lon1_deg).to_radians();
    let y = delta_lon.sin() * lat2_rad.cos();
    let x = lat1_rad.cos() * lat2_rad.sin() - lat1_rad.sin() * lat2_rad.cos() * delta_lon.cos();
    let bearing_rad = y.atan2(x);
    let bearing_deg = (bearing_rad.to_degrees() + 360.0) % 360.0;
    Ok(bearing_deg)
}

// Approximation of the perpindicular deviation distance from course in meters.
// Calculated from the right angle triangle formed between course line and line from
// course start to position.
#[pyfunction]
pub fn deviation_from_course_meters(
    course_lat1_deg: f64,
    course_lon1_deg: f64,
    course_lat2_deg: f64,
    course_lon2_deg: f64,
    pos_lat_deg: f64,
    pos_lon_deg: f64,
) -> PyResult<f64> {
    let course_bearing = bearing_deg(
        course_lat1_deg,
        course_lon1_deg,
        course_lat2_deg,
        course_lon2_deg,
    )?;
    let pos_bearing = bearing_deg(course_lat1_deg, course_lon1_deg, pos_lat_deg, pos_lon_deg)?;
    let dist_to_course_pt1 =
        haversine_distance_meters(course_lat1_deg, course_lon1_deg, pos_lat_deg, pos_lon_deg)?;
    let mut angle_diff = (pos_bearing - course_bearing) % 360.0;
    if angle_diff > 180.0 {
        angle_diff -= 360.0;
    }
    // Perpendicular distance is opposite side of right triangle with hypotenuse as
    // distance from course start point to position and theta as the difference in
    // bearings between course and the line from course start to position.
    let deviation = dist_to_course_pt1 * angle_diff.to_radians().sin();
    Ok(deviation)
}
