use crate::coordinate_system::geo::{Ellipsoid, Geoid, OffsetMap};
use pyo3::prelude::*;

// -------------------------------------------------------------------------------
// Renderer Coordinate Frame Conversions

// TODO Generalize these from Unreal-specific to conversions between Z vs Y up axis
// and LHS vs RHS coordinate systems, and meters vs centimeters per unit to cover
// various renderers.

pub fn ned_to_unreal_esu(north: f64, east: f64, down: f64) -> (f64, f64, f64) {
    // NED -> ESU, m -> cm
    (east * 100.0, -north * 100.0, -down * 100.0)
}

pub fn rpy_ned_to_unreal_esu(roll: f64, pitch: f64, yaw: f64) -> (f64, f64, f64) {
    // NED -> ESU
    let yaw_rotated = yaw - (90_f64).to_radians();
    let yaw_norm = (yaw_rotated + std::f64::consts::TAU) % std::f64::consts::TAU;
    (roll, pitch, yaw_norm)
}

// Omniverse Cesium with Z-up stage uses X=East, Y=North, Z=Up with 1 m per unit
//   Position: NED -> Omniverse Z-up -> Cesium ENU = NED -> NWU -> ENU
//   Rotation: FRD -> Omniverse Z-up -> Cesium ENU = FRD -> FLU (NWU) -> ENU

pub fn ned_to_nwu(north: f64, east: f64, down: f64) -> (f64, f64, f64) {
    (north, -east, -down)
}

pub fn nwu_to_enu(north: f64, west: f64, up: f64) -> (f64, f64, f64) {
    (-west, north, up)
}

pub fn ned_to_enu(north: f64, east: f64, down: f64) -> (f64, f64, f64) {
    (east, north, -down)
}

pub fn frd_to_flu(front: f64, right: f64, down: f64) -> (f64, f64, f64) {
    (front, -right, -down)
}

pub fn rpy_frd_to_flu(roll: f64, pitch: f64, yaw: f64) -> (f64, f64, f64) {
    // Angles in radians, FRD -> FLU
    (roll, -pitch, -yaw)
}

pub fn rpy_nwu_to_enu(roll: f64, pitch: f64, yaw: f64) -> (f64, f64, f64) {
    // Angles in radians, NWU -> ENU for Cesium
    let yaw_rotated = yaw + std::f64::consts::FRAC_PI_2;
    let yaw_norm = (yaw_rotated + std::f64::consts::TAU) % std::f64::consts::TAU;
    (roll, pitch, yaw_norm)
}

// -------------------------------------------------------------------------------
// Geocoordinate System Conversions

#[pyfunction]
#[pyo3(signature = (lat, lon, alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn lla_to_ecef(lat: f64, lon: f64, alt: f64, ellipsoid: Ellipsoid) -> (f64, f64, f64) {
    let cos_lat = lat.to_radians().cos();
    let sin_lat = lat.to_radians().sin();
    let cos_lon = lon.to_radians().cos();
    let sin_lon = lon.to_radians().sin();

    let e2 = ellipsoid.flattening_factor * (2.0 - ellipsoid.flattening_factor);
    let n = ellipsoid.equatorial_radius / (1.0 - e2 * sin_lat * sin_lat).sqrt();

    let x = (n + alt) * cos_lat * cos_lon;
    let y = (n + alt) * cos_lat * sin_lon;
    let z = ((1.0 - ellipsoid.flattening_factor) * (1.0 - ellipsoid.flattening_factor) * n + alt)
        * sin_lat;

    (x, y, z)
}

#[pyfunction]
#[pyo3(signature = (ecef_x, ecef_y, ecef_z, ellipsoid=Ellipsoid::wgs84()))]
pub fn ecef_to_lla(ecef_x: f64, ecef_y: f64, ecef_z: f64, ellipsoid: Ellipsoid) -> (f64, f64, f64) {
    let e2 = (ellipsoid.equatorial_radius.powi(2) - ellipsoid.polar_radius.powi(2))
        / ellipsoid.equatorial_radius.powi(2);
    let ep2 = (ellipsoid.equatorial_radius.powi(2) - ellipsoid.polar_radius.powi(2))
        / ellipsoid.polar_radius.powi(2);

    let p = (ecef_x.powi(2) + ecef_y.powi(2)).sqrt();
    let theta = (ecef_z * ellipsoid.equatorial_radius / (p * ellipsoid.polar_radius)).atan();

    let mut lat = (ecef_z + ep2 * ellipsoid.polar_radius * theta.sin().powi(3))
        .atan2(p - e2 * ellipsoid.equatorial_radius * theta.cos().powi(3));
    let mut lon = ecef_y.atan2(ecef_x);

    let n = ellipsoid.equatorial_radius / (1.0 - e2 * lat.sin().powi(2)).sqrt();
    let alt = p / lat.cos() - n;

    lat = lat.to_degrees();
    lon = lon.to_degrees();

    (lat, lon, alt)
}

#[pyfunction]
#[pyo3(signature = (north, east, down, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn ned_to_ecef(
    north: f64,
    east: f64,
    down: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (origin_ecef_x, origin_ecef_y, origin_ecef_z) =
        lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);

    let cos_lat = origin_lat.to_radians().cos();
    let sin_lat = origin_lat.to_radians().sin();
    let cos_lon = origin_lon.to_radians().cos();
    let sin_lon = origin_lon.to_radians().sin();

    let dx = -sin_lat * cos_lon * north - sin_lon * east - cos_lat * cos_lon * down;
    let dy = -sin_lat * sin_lon * north + cos_lon * east - cos_lat * sin_lon * down;
    let dz = cos_lat * north - sin_lat * down;

    (origin_ecef_x + dx, origin_ecef_y + dy, origin_ecef_z + dz)
}

#[pyfunction]
#[pyo3(signature = (ecef_x, ecef_y, ecef_z, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn ecef_to_ned(
    ecef_x: f64,
    ecef_y: f64,
    ecef_z: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (origin_ecef_x, origin_ecef_y, origin_ecef_z) =
        lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);
    let (dx, dy, dz) = (
        ecef_x - origin_ecef_x,
        ecef_y - origin_ecef_y,
        ecef_z - origin_ecef_z,
    );

    let cos_lat = origin_lat.to_radians().cos();
    let sin_lat = origin_lat.to_radians().sin();
    let cos_lon = origin_lon.to_radians().cos();
    let sin_lon = origin_lon.to_radians().sin();

    let north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz;
    let east = -sin_lon * dx + cos_lon * dy;
    let down = -cos_lat * cos_lon * dx - cos_lat * sin_lon * dy - sin_lat * dz;

    (north, east, down)
}

#[pyfunction]
#[pyo3(signature = (lat, lon, alt, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn lla_to_ned(
    lat: f64,
    lon: f64,
    alt: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (ecef_x, ecef_y, ecef_z) = lla_to_ecef(lat, lon, alt, ellipsoid);
    ecef_to_ned(
        ecef_x, ecef_y, ecef_z, origin_lat, origin_lon, origin_alt, ellipsoid,
    )
}

#[pyfunction]
#[pyo3(signature = (north, east, down, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn ned_to_lla(
    north: f64,
    east: f64,
    down: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (ecef_x, ecef_y, ecef_z) = ned_to_ecef(
        north, east, down, origin_lat, origin_lon, origin_alt, ellipsoid,
    );
    ecef_to_lla(ecef_x, ecef_y, ecef_z, ellipsoid)
}

#[pyfunction]
#[pyo3(signature = (lat, lon, alt, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn lla_to_cartesian(
    lat: f64,
    lon: f64,
    alt: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (point_x, point_y, point_z) = lla_to_ecef(lat, lon, alt, ellipsoid);
    let (origin_x, origin_y, origin_z) = lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);

    let cartesian_x = point_x - origin_x;
    let cartesian_y = point_y - origin_y;
    let cartesian_z = point_z - origin_z;

    (cartesian_x, cartesian_y, cartesian_z)
}

#[pyfunction]
#[pyo3(signature = (north, east, down, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn ned_to_cartesian(
    north: f64,
    east: f64,
    down: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (ecef_x, ecef_y, ecef_z) = ned_to_ecef(
        north, east, down, origin_lat, origin_lon, origin_alt, ellipsoid,
    );
    let (origin_x, origin_y, origin_z) = lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);

    let cartesian_x = ecef_x - origin_x;
    let cartesian_y = ecef_y - origin_y;
    let cartesian_z = ecef_z - origin_z;

    (cartesian_x, cartesian_y, cartesian_z)
}

#[pyfunction]
#[pyo3(signature = (point_x, point_y, point_z, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn cartesian_to_ned(
    point_x: f64,
    point_y: f64,
    point_z: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (origin_x, origin_y, origin_z) = lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);
    let (ecef_x, ecef_y, ecef_z) = (origin_x + point_x, origin_y + point_y, origin_z + point_z);

    ecef_to_ned(
        ecef_x, ecef_y, ecef_z, origin_lat, origin_lon, origin_alt, ellipsoid,
    )
}

#[pyfunction]
#[pyo3(signature = (point_x, point_y, point_z, origin_lat, origin_lon, origin_alt, ellipsoid=Ellipsoid::wgs84()))]
pub fn cartesian_to_lla(
    point_x: f64,
    point_y: f64,
    point_z: f64,
    origin_lat: f64,
    origin_lon: f64,
    origin_alt: f64,
    ellipsoid: Ellipsoid,
) -> (f64, f64, f64) {
    let (origin_x, origin_y, origin_z) = lla_to_ecef(origin_lat, origin_lon, origin_alt, ellipsoid);
    let (ecef_x, ecef_y, ecef_z) = (origin_x + point_x, origin_y + point_y, origin_z + point_z);

    ecef_to_lla(ecef_x, ecef_y, ecef_z, ellipsoid)
}

#[pyfunction]
#[pyo3(signature = (lat, lon, alt, geoid))]
pub fn msl_to_hae(lat: f64, lon: f64, alt: f64, geoid: &Geoid) -> f64 {
    let geoid_height = geoid.get_geoid_height(lat, lon);

    let hae_altitude = alt + geoid_height;
    hae_altitude
}

#[pyfunction]
#[pyo3(signature = (lat, lon, alt, geoid))]
pub fn hae_to_msl(lat: f64, lon: f64, alt: f64, geoid: &Geoid) -> f64 {
    let geoid_height = geoid.get_geoid_height(lat, lon);

    let msl_altitude = alt - geoid_height;
    msl_altitude
}

#[pyfunction]
pub fn msl_to_hae_with_offset(
    lat: f64,
    lon: f64,
    alt: f64,
    geoid: &Geoid,
    offset_map: &OffsetMap,
) -> f64 {
    let geoid_height = geoid.get_geoid_height(lat, lon);
    let offset = offset_map.get_offset(lat, lon);

    let hae_altitude = alt + geoid_height - offset;
    hae_altitude
}

#[pyfunction]
pub fn hae_to_msl_with_offset(
    lat: f64,
    lon: f64,
    alt: f64,
    geoid: &Geoid,
    offset_map: &OffsetMap,
) -> f64 {
    let geoid_height = geoid.get_geoid_height(lat, lon);
    let offset = offset_map.get_offset(lat, lon);

    let msl_altitude = alt - geoid_height + offset;
    msl_altitude
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_approx_eq(expected: f64, actual: f64, tolerance: f64, name: &str) {
        assert!(
            (expected - actual).abs() < tolerance,
            "{} is incorrect: expected {}, got {}",
            name,
            expected,
            actual,
        );
    }

    macro_rules! test_lla_to_ecef {
        ($($id:ident: ($lat:expr, $lon:expr, $h:expr) => ($expected_x:expr, $expected_y:expr, $expected_z:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (ecef_x, ecef_y, ecef_z) = lla_to_ecef($lat, $lon, $h, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_x, ecef_x, tolerance, "ECEF X");
                    assert_approx_eq($expected_y, ecef_y, tolerance, "ECEF Y");
                    assert_approx_eq($expected_z, ecef_z, tolerance, "ECEF Z");
                }
            )+
        };
    }

    macro_rules! test_ecef_to_ned {
        ($($id:ident: ($x:expr, $y:expr, $z:expr, $lat0:expr, $lon0:expr, $h0:expr) => ($expected_n:expr, $expected_e:expr, $expected_d:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (ned_x, ned_y, ned_z) = ecef_to_ned($x, $y, $z, $lat0, $lon0, $h0, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_n, ned_x, tolerance, "NED North");
                    assert_approx_eq($expected_e, ned_y, tolerance, "NED East");
                    assert_approx_eq($expected_d, ned_z, tolerance, "NED Down");
                }
            )+
        };
    }

    macro_rules! test_lla_to_ned {
        ($($id:ident: ($lat:expr, $lon:expr, $h:expr, $lat0:expr, $lon0:expr, $h0:expr) => ($expected_n:expr, $expected_e:expr, $expected_d:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (ned_x, ned_y, ned_z) = lla_to_ned($lat, $lon, $h, $lat0, $lon0, $h0, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_n, ned_x, tolerance, "NED North");
                    assert_approx_eq($expected_e, ned_y, tolerance, "NED East");
                    assert_approx_eq($expected_d, ned_z, tolerance, "NED Down");
                }
            )+
        };
    }

    macro_rules! test_ned_to_ecef {
        ($($id:ident: ($north:expr, $east:expr, $down:expr, $lat0:expr, $lon0:expr, $h0:expr) => ($expected_x:expr, $expected_y:expr, $expected_z:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (ecef_x, ecef_y, ecef_z) = ned_to_ecef($north, $east, $down, $lat0, $lon0, $h0, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_x, ecef_x, tolerance, "ECEF X");
                    assert_approx_eq($expected_y, ecef_y, tolerance, "ECEF Y");
                    assert_approx_eq($expected_z, ecef_z, tolerance, "ECEF Z");
                }
            )+
        };
    }

    macro_rules! test_ecef_to_lla {
        ($($id:ident: ($x:expr, $y:expr, $z:expr) => ($expected_lat:expr, $expected_lon:expr, $expected_h:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (lat, lon, alt) = ecef_to_lla($x, $y, $z, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_lat, lat, tolerance, "Latitude");
                    assert_approx_eq($expected_lon, lon, tolerance, "Longitude");
                    assert_approx_eq($expected_h, alt, tolerance, "Altitude");
                }
            )+
        };
    }

    macro_rules! test_ned_to_lla {
        ($($id:ident: ($north:expr, $east:expr, $down:expr, $lat0:expr, $lon0:expr, $h0:expr) => ($expected_lat:expr, $expected_lon:expr, $expected_h:expr)),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let ellipsoid = Ellipsoid::wgs84();
                    let (lat, lon, alt)  = ned_to_lla($north, $east, $down, $lat0, $lon0, $h0, ellipsoid);
                    let tolerance = 1e-2;
                    assert_approx_eq($expected_lat, lat, tolerance, "Latitude");
                    assert_approx_eq($expected_lon, lon, tolerance, "Longitude");
                    assert_approx_eq($expected_h, alt, tolerance, "Altitude");
                }
            )+
        };
    }

    macro_rules! test_msl_to_hae {
        ($($id:ident: ($lat:expr, $lon:expr, $msl_alt:expr) => $expected_hae:expr),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let geoid = Geoid::egm08();
                    let result_hae = msl_to_hae($lat, $lon, $msl_alt, &geoid);
                    let tolerance = 5.0;
                    assert!((result_hae - $expected_hae).abs() < tolerance,
                        "Test {} failed: expected HAE {} but got {}", stringify!($id), $expected_hae, result_hae);
                }
            )+
        };
    }

    macro_rules! test_hae_to_msl {
        ($($id:ident: ($lat:expr, $lon:expr, $hae_alt:expr) => $expected_msl:expr),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let geoid = Geoid::egm08();
                    let result_msl = hae_to_msl($lat, $lon, $hae_alt, &geoid);
                    let tolerance = 5.0;
                    assert!((result_msl - $expected_msl).abs() < tolerance,
                        "Test {} failed: expected MSL {} but got {}", stringify!($id), $expected_msl, result_msl);
                }
            )+
        };
    }

    macro_rules! test_msl_to_hae_with_offset {
        ($($id:ident: ($lat:expr, $lon:expr, $msl_alt:expr, $json_file:expr) => $expected_hae:expr),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let geoid = Geoid::egm08();
                    let offset_map = OffsetMap::from_json($json_file);
                    let result_hae = msl_to_hae_with_offset($lat, $lon, $msl_alt, &geoid, &offset_map);
                    let tolerance = 1e-1;
                    assert!((result_hae - $expected_hae).abs() < tolerance,
                        "Test {} failed: expected HAE {} but got {}", stringify!($id), $expected_hae, result_hae);
                }
            )+
        };
    }

    macro_rules! test_get_offset {
        ($($id:ident: ($lat:expr, $lon:expr, $json_file:expr) => $expected_offset:expr),+ $(,)?) => {
            $(
                #[test]
                fn $id() {
                    let offset_map = OffsetMap::from_json($json_file);
                    let offset = offset_map.get_offset($lat, $lon);
                    let tolerance = 1e-1;
                    assert!((offset - $expected_offset).abs() < tolerance,
                        "Test {} failed: expected offset {} but got {}", stringify!($id), $expected_offset, offset);
                }
            )+
        };
    }

    test_lla_to_ecef! {
        test_lla_to_ecef_0: (44.532, -72.814, 1340.0) => (1345937.25, -4351784.71, 4451363.50),
    }

    test_ecef_to_ned! {
        test_ecef_to_ned_0: (1345937.25, -4351784.71, 4451363.50, 44.532, -72.782, 1699.0) => (0.4997, -2.544087e3, 359.5123),
    }

    test_lla_to_ned! {
        test_lla_to_ned_0: (44.532, -72.814, 1340.0, 44.532, -72.782, 1699.0) => (0.4997, -2.544087e3, 359.5123),
    }

    test_ned_to_ecef! {
        test_ned_to_ecef_0: (0.4997, -2544.087, 359.5123, 44.532, -72.782, 1699.0) => (1345937.25, -4351784.71, 4451363.50),
    }

    test_ecef_to_lla! {
        test_ecef_to_lla_0: (1345937.25, -4351784.71, 4451363.50) => (44.532, -72.814, 1340.0),
    }

    test_ned_to_lla! {
        test_ned_to_lla_0: (0.4997, -2544.087, 359.5123, 44.532, -72.782, 1699.0) => (44.532, -72.814, 1340.0),
    }

    test_msl_to_hae! {
        test_msl_to_hae_lax_0: (33.9335511, -118.401695, 30.0) => -6.03,
        test_msl_to_hae_lax_1: (33.952055, -118.402549, 37.0) => 1.02,
        test_msl_to_hae_lax_2: (33.939739, -118.380871, 31.0) => -4.99,
        test_msl_to_hae_lax_3: (33.933703, -118.418282, 34.0) => 2.04,
        test_msl_to_hae_lax_4: (33.942487, -118.412197, 39.0) => 2.98,

        test_msl_to_hae_0: (-37.813628, 144.963058, 2.37) => 7.00,
        test_msl_to_hae_1: (-34.603722, -58.381592, 9.04) => 25.00,
        test_msl_to_hae_2: (-33.86882, 151.209296, 35.65) => 58.00,
        test_msl_to_hae_3: (-23.55052, -46.633308, 763.25) => 760.00,
        test_msl_to_hae_4: (19.432608, -99.133209, 2245.44) => 2240.00,
        test_msl_to_hae_5: (28.613939, 77.209023, 268.55) => 216.00,
        test_msl_to_hae_6: (35.689487, 139.691711, 3.29) => 40.00,
        test_msl_to_hae_7: (40.712776, -74.005974, 42.73) => 10.00,
        test_msl_to_hae_8: (48.8588443, 2.2943506, 0.36) => 45.00,
        test_msl_to_hae_9: (55.755825, 37.617298, 129.46) => 144.00,
    }

    test_hae_to_msl! {
        test_hae_to_msl_0: (-37.813628, 144.963058, 7.00) => 2.37,
        test_hae_to_msl_1: (-34.603722, -58.381592, 25.00) => 9.04,
        test_hae_to_msl_2: (-33.86882, 151.209296, 58.00) => 35.65,
        test_hae_to_msl_3: (-23.55052, -46.633308, 760.00) => 763.25,
        test_hae_to_msl_4: (19.432608, -99.133209, 2240.00) => 2245.44,
        test_hae_to_msl_5: (28.613939, 77.209023, 216.00) => 268.55,
        test_hae_to_msl_6: (35.689487, 139.691711, 40.00) => 3.29,
        test_hae_to_msl_7: (40.712776, -74.005974, 10.00) => 42.73,
        test_hae_to_msl_8: (48.8588443, 2.2943506, 45.00) => 0.36,
        test_hae_to_msl_9: (55.755825, 37.617298, 144.00) => 129.46,
    }

    test_get_offset! {
        test_get_offset_18: (33.9335511, -118.401695, "tests/offset_map.json") => -2.48,
        test_get_offset_19: (33.952055, -118.402549, "tests/offset_map.json") => 3.21,
        test_get_offset_20: (33.939739, -118.380871, "tests/offset_map.json") => 4.63,
        test_get_offset_21: (33.933703, -118.418282, "tests/offset_map.json") => -0.62,
        test_get_offset_22: (33.942487, -118.412197, "tests/offset_map.json") => 5.3155,
    }

    test_msl_to_hae_with_offset! {
        test_msl_to_hae_with_offset_0: (33.9335511, -118.401695, 30.0, "tests/offset_map.json") => -1.9,
        test_msl_to_hae_with_offset_1: (33.952055, -118.402549, 37.0, "tests/offset_map.json") => -0.62,
        test_msl_to_hae_with_offset_2: (33.939739, -118.380871, 31.0, "tests/offset_map.json") => -8.05,
        test_msl_to_hae_with_offset_3: (33.933703, -118.418282, 34.0, "tests/offset_map.json") => 0.175,
        test_msl_to_hae_with_offset_4: (33.942487, -118.412197, 39.0, "tests/offset_map.json") => -0.8,
    }
}
