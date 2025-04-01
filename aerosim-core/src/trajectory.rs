use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::{error::Error, io::Write};

use aerosim_data::types::{ActorState, Pose, Quaternion, TimeStamp, Vector3, VehicleState};

use csv::Reader;
use pyo3::prelude::*;

use crate::{
    coordinate_system::conversion_utils,
    lla_to_ned,
    math::{self},
    Ellipsoid, Geoid,
};

struct CubicSpline {
    times: Vec<f64>,
    coefficients: Vec<(f64, f64, f64, f64)>,
}

impl CubicSpline {
    fn interpolate(&self, t: f64) -> f64 {
        let i = match self
            .times
            .binary_search_by(|time| time.partial_cmp(&t).unwrap())
        {
            Ok(idx) => idx.min(self.times.len() - 2),
            Err(idx) => idx.saturating_sub(1).min(self.times.len() - 2),
        };

        let dt = t - self.times[i];
        let (a, b, c, d) = self.coefficients[i];

        let value = a + b * dt + c * dt.powi(2) + d * dt.powi(3);
        value
    }
}

fn generate_cubic_spline(times: &[f64], values: &[f64]) -> CubicSpline {
    let n = times.len() - 1;

    let h: Vec<f64> = times.windows(2).map(|w| w[1] - w[0]).collect();
    let alpha: Vec<f64> = (1..n)
        .map(|i| {
            3.0 * (values[i + 1] - values[i]) / h[i] - 3.0 * (values[i] - values[i - 1]) / h[i - 1]
        })
        .collect();

    let mut l = vec![1.0; n + 1];
    let mut mu = vec![0.0; n];
    let mut z = vec![0.0; n + 1];

    for i in 1..n {
        l[i] = 2.0 * (times[i + 1] - times[i - 1]) - h[i - 1] * mu[i - 1];
        mu[i] = h[i] / l[i];
        z[i] = (alpha[i - 1] - h[i - 1] * z[i - 1]) / l[i];
    }

    let mut c = vec![0.0; n + 1];
    let mut b = vec![0.0; n];
    let mut d = vec![0.0; n];
    let mut coefficients = Vec::with_capacity(n);

    for j in (0..n).rev() {
        c[j] = z[j] - mu[j] * c[j + 1];
        b[j] = (values[j + 1] - values[j]) / h[j] - h[j] * (c[j + 1] + 2.0 * c[j]) / 3.0;
        d[j] = (c[j + 1] - c[j]) / (3.0 * h[j]);
        coefficients.push((values[j], b[j], c[j], d[j]));
    }

    coefficients.reverse();

    CubicSpline {
        times: times.to_vec(),
        coefficients,
    }
}

/// Generate a trajectory from a set of points
/// points: list of (time (in seconds), latitude (in degrees), longitude (in degrees), altitude (in meters),optional roll (in degrees),optional pitch (in degrees),optional yaw (in degrees), optional is_ground_point (bool))
/// time_step: time step between each generated point (in seconds)
/// origin_latlonalt: optional origin latitude, longitude, altitude, defaults to first point
/// ellipsoid: optional ellipsoid, defaults to WGS84
/// returns: list of vehicle states
#[pyfunction]
#[pyo3(signature = (
    points,
    time_step,
    max_roll_rate_deg_per_second = 10.0,
    curvature_to_roll_factor = 1.0,
    origin_latlonalt = None,
    ellipsoid = Ellipsoid::wgs84()
))]
pub fn generate_trajectory(
    // Each point: (time, lat, lon, alt, Option(roll), Option(pitch), Option(yaw), Option(is_ground_point))
    points: Vec<(
        f64,
        f64,
        f64,
        f64,
        Option<f64>,
        Option<f64>,
        Option<f64>,
        Option<bool>,
    )>,
    time_step: f64,
    max_roll_rate_deg_per_second: f64,
    curvature_to_roll_factor: f64,
    origin_latlonalt: Option<(f64, f64, f64)>,
    ellipsoid: Ellipsoid,
) -> PyResult<Vec<(TimeStamp, VehicleState)>> {
    if points.len() < 4 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Spline trajectory requires at least 4 points",
        ));
    }

    let mut sorted_points = points;
    sorted_points.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let origin_ll =
        origin_latlonalt.unwrap_or((sorted_points[0].1, sorted_points[0].2, sorted_points[0].3));

    let control_points: Vec<(Vector3, f64, Option<f64>, Option<f64>, Option<f64>, bool)> =
        sorted_points
            .into_iter()
            .map(
                |(t, lat, lon, alt, maybe_roll, maybe_pitch, maybe_yaw, maybe_ground)| {
                    let pos = lla_to_ned(
                        lat,
                        lon,
                        alt,
                        origin_ll.0,
                        origin_ll.1,
                        origin_ll.2,
                        ellipsoid,
                    );
                    (
                        Vector3::new(pos.0, pos.1, pos.2),
                        t,
                        maybe_roll,
                        maybe_pitch,
                        maybe_yaw,
                        maybe_ground.unwrap_or(false),
                    )
                },
            )
            .collect();

    // Extraemos los vectores de posición y tiempos para generar los splines de x, y, z
    let mut x_values = Vec::with_capacity(control_points.len());
    let mut y_values = Vec::with_capacity(control_points.len());
    let mut z_values = Vec::with_capacity(control_points.len());
    let mut t_values = Vec::with_capacity(control_points.len());
    for (pos, t, _, _, _, _) in &control_points {
        x_values.push(pos.x);
        y_values.push(pos.y);
        z_values.push(pos.z);
        t_values.push(*t);
    }

    let spline_x = generate_cubic_spline(&t_values, &x_values);
    let spline_y = generate_cubic_spline(&t_values, &y_values);
    let spline_z = generate_cubic_spline(&t_values, &z_values);

    let mut trajectory = Vec::new();
    let mut prev_state: Option<VehicleState> = None;
    let mut stamp = TimeStamp::new(0, 0);
    let last_time = *t_values.last().unwrap();
    let mut current_time = time_step;

    while current_time <= last_time {
        let x = spline_x.interpolate(current_time);
        let y = spline_y.interpolate(current_time);
        let z = spline_z.interpolate(current_time);
        let position = Vector3::new(x, y, z);

        let velocity = if current_time + time_step <= last_time {
            let nx = spline_x.interpolate(current_time + time_step);
            let ny = spline_y.interpolate(current_time + time_step);
            let nz = spline_z.interpolate(current_time + time_step);
            Vector3 {
                x: (nx - x) / time_step,
                y: (ny - y) / time_step,
                z: (nz - z) / time_step,
            }
        } else if let Some(prev) = &prev_state {
            let prev_pos = prev.state.pose.position;
            Vector3 {
                x: (x - prev_pos.x) / time_step,
                y: (y - prev_pos.y) / time_step,
                z: (z - prev_pos.z) / time_step,
            }
        } else {
            Vector3::default()
        };

        let seg_index =
            match t_values.binary_search_by(|val| val.partial_cmp(&current_time).unwrap()) {
                Ok(idx) => {
                    if idx == t_values.len() - 1 {
                        idx - 1
                    } else {
                        idx
                    }
                }
                Err(idx) => {
                    if idx == 0 {
                        0
                    } else {
                        idx - 1
                    }
                }
            };
        let (_, t0, _roll0, _pitch0, _yaw0, _) = control_points[seg_index];
        let (_, t1, target_roll, target_pitch, target_yaw, target_ground) =
            control_points[seg_index + 1];
        let segment_duration = t1 - t0;
        let alpha = if segment_duration.abs() > std::f64::EPSILON {
            (current_time - t0) / segment_duration
        } else {
            1.0
        };

        let orientation = if target_roll.is_some() && target_pitch.is_some() && target_yaw.is_some()
        {
            let effective_roll = if target_ground {
                0.0
            } else {
                target_roll.unwrap_or(0.0)
            };
            let effective_pitch = target_pitch.unwrap_or(0.0);
            let effective_yaw = target_yaw.unwrap_or(0.0);

            let target_quat = crate::math::quaternion::Quaternion::from_euler_angles(
                [effective_roll.to_radians(), effective_pitch, effective_yaw],
                crate::math::quaternion::RotationType::Extrinsic,
                crate::math::quaternion::RotationSequence::ZYX,
            );

            let source_quat = if let Some(prev) = &prev_state {
                let prev_ori = prev.state.pose.orientation;
                crate::math::quaternion::Quaternion::new(
                    prev_ori.w, prev_ori.x, prev_ori.y, prev_ori.z,
                )
            } else {
                let next_time = current_time + time_step;
                if next_time <= last_time {
                    let nx = spline_x.interpolate(next_time);
                    let ny = spline_y.interpolate(next_time);
                    let nz = spline_z.interpolate(next_time);
                    let (_, pitch, yaw) = compute_rpy_with_level_roll(
                        math::Vector3::from_vector3_data(position),
                        math::Vector3::new(nx, ny, nz),
                    );
                    crate::math::quaternion::Quaternion::from_euler_angles(
                        [0.0, pitch, yaw],
                        crate::math::quaternion::RotationType::Extrinsic,
                        crate::math::quaternion::RotationSequence::ZYX,
                    )
                } else {
                    crate::math::quaternion::Quaternion::new(1.0, 0.0, 0.0, 0.0)
                }
            };
            let interp_quat = slerp(source_quat, target_quat, alpha);
            Quaternion {
                w: interp_quat.w(),
                x: interp_quat.x(),
                y: interp_quat.y(),
                z: interp_quat.z(),
            }
        } else {
            let next_time = current_time + time_step;
            if next_time <= last_time {
                let nx = spline_x.interpolate(next_time);
                let ny = spline_y.interpolate(next_time);
                let nz = spline_z.interpolate(next_time);
                let (_, pitch, yaw) = compute_rpy_with_level_roll(
                    math::Vector3::from_vector3_data(position),
                    math::Vector3::new(nx, ny, nz),
                );
                let roll = if let Some(prev) = &prev_state {
                    let curvature = calculate_curvature(
                        math::Vector3::from_vector3_data(prev.state.pose.position),
                        math::Vector3::from_vector3_data(position),
                        math::Vector3::new(nx, ny, nz),
                    );
                    let v_length = (velocity.x * velocity.x
                        + velocity.y * velocity.y
                        + velocity.z * velocity.z)
                        .sqrt();
                    let computed_roll =
                        (v_length * v_length * curvature).atan() * curvature_to_roll_factor;
                    let prev_ori = prev.state.pose.orientation;
                    let quat_prev = crate::math::quaternion::Quaternion::new(
                        prev_ori.w, prev_ori.x, prev_ori.y, prev_ori.z,
                    );
                    let prev_roll = quat_prev.to_euler_angles(
                        crate::math::quaternion::RotationType::Extrinsic,
                        crate::math::quaternion::RotationSequence::ZYX,
                    )[0];
                    let roll_diff = computed_roll - prev_roll;
                    let max_roll_inc = max_roll_rate_deg_per_second.to_radians() * time_step;
                    prev_roll
                        + if roll_diff.abs() > max_roll_inc {
                            max_roll_inc * roll_diff.signum()
                        } else {
                            roll_diff
                        }
                } else {
                    0.0
                };
                let quat = crate::math::quaternion::Quaternion::from_euler_angles(
                    [roll, pitch, yaw],
                    crate::math::quaternion::RotationType::Extrinsic,
                    crate::math::quaternion::RotationSequence::ZYX,
                );
                Quaternion {
                    w: quat.w(),
                    x: quat.x(),
                    y: quat.y(),
                    z: quat.z(),
                }
            } else {
                prev_state
                    .as_ref()
                    .map_or(Quaternion::default(), |state| state.state.pose.orientation)
            }
        };

        let state = create_vehicle_state(position, orientation, velocity, &prev_state, time_step);
        prev_state = Some(state.clone());
        trajectory.push((stamp, state));
        increment_stamp(&mut stamp, time_step);
        current_time += time_step;
    }

    let last_idx = t_values.len() - 1;
    let final_position = Vector3::new(x_values[last_idx], y_values[last_idx], z_values[last_idx]);
    if trajectory.last().map_or(true, |(_, state)| {
        state.state.pose.position != final_position
    }) {
        let (_, _, maybe_roll, maybe_pitch, maybe_yaw, ground_flag) = control_points[last_idx];
        let final_orientation =
            if maybe_roll.is_some() && maybe_pitch.is_some() && maybe_yaw.is_some() {
                let effective_roll = if ground_flag {
                    0.0
                } else {
                    maybe_roll.unwrap_or(0.0)
                };
                let effective_pitch = maybe_pitch.unwrap_or(0.0);
                let effective_yaw = maybe_yaw.unwrap_or(0.0);
                let quat = crate::math::quaternion::Quaternion::from_euler_angles(
                    [effective_roll.to_radians(), effective_pitch, effective_yaw],
                    crate::math::quaternion::RotationType::Extrinsic,
                    crate::math::quaternion::RotationSequence::ZYX,
                );
                Quaternion {
                    w: quat.w(),
                    x: quat.x(),
                    y: quat.y(),
                    z: quat.z(),
                }
            } else {
                prev_state
                    .as_ref()
                    .map_or(Quaternion::default(), |state| state.state.pose.orientation)
            };
        trajectory.push((
            stamp,
            create_vehicle_state(
                final_position,
                final_orientation,
                Vector3::default(),
                &None,
                time_step,
            ),
        ));
    }

    Ok(trajectory)
}

/// Generate a linear interpolated trajectory from a set of points
/// points: list of (time (in seconds), latitude (in degrees), longitude (in degrees), altitude (in meters))
/// time_step: time step between each generated point (in seconds)
/// origin_latlonalt: optional origin latitude, longitude, altitude, defaults to first point
/// ellipsoid: optional ellipsoid, defaults to WGS84
/// returns: list of vehicle states
#[pyfunction]
#[pyo3(signature = (points, time_step, origin_latlonalt=None, ellipsoid=Ellipsoid::wgs84()))]
pub fn generate_trajectory_linear(
    points: Vec<(f64, f64, f64, f64)>,
    time_step: f64,
    origin_latlonalt: Option<(f64, f64, f64)>,
    ellipsoid: Ellipsoid,
) -> PyResult<Vec<(TimeStamp, VehicleState)>> {
    if points.len() < 2 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "trajectory must have at least 2 points",
        ));
    }

    let vec_points: Vec<(Vector3, f64)> = points
        .iter()
        .map(|(t, x, y, z)| {
            (
                Vector3 {
                    x: *x,
                    y: *y,
                    z: *z,
                },
                *t,
            )
        })
        .collect();

    let origin_ll = origin_latlonalt.unwrap_or((
        vec_points.first().unwrap().0.x,
        vec_points.first().unwrap().0.y,
        vec_points.first().unwrap().0.z,
    ));

    let mut stamp = TimeStamp::new(0, 0);
    let mut trajectory = Vec::new();
    let mut prev_state: Option<VehicleState> = None;

    for i in 0..vec_points.len() - 1 {
        let (start_pos, start_time) = vec_points[i];
        let (end_pos, end_time) = vec_points[i + 1];

        let start = lla_to_ned(
            start_pos.x,
            start_pos.y,
            start_pos.z,
            origin_ll.0,
            origin_ll.1,
            origin_ll.2,
            ellipsoid,
        );
        let start = math::Vector3::new(start.0, start.1, start.2);
        let end = lla_to_ned(
            end_pos.x,
            end_pos.y,
            end_pos.z,
            origin_ll.0,
            origin_ll.1,
            origin_ll.2,
            ellipsoid,
        );
        let end = math::Vector3::new(end.0, end.1, end.2);

        let dx = end.x - start.x;
        let dy = end.y - start.y;
        let dz = end.z - start.z;

        let (roll, pitch, yaw) = compute_rpy_with_level_roll(start, end);
        let quat = crate::math::quaternion::Quaternion::from_euler_angles(
            [roll, pitch, yaw],
            crate::math::quaternion::RotationType::Extrinsic,
            crate::math::quaternion::RotationSequence::ZYX,
        );
        let orientation = Quaternion {
            w: quat.w(),
            x: quat.x(),
            y: quat.y(),
            z: quat.z(),
        };

        let total_time = end_time - start_time;
        if total_time <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Invalid time values: end_time must be greater than start_time",
            ));
        }

        let velocity_vector = Vector3 {
            x: dx / total_time,
            y: dy / total_time,
            z: dz / total_time,
        };
        let step_count = (total_time / time_step).ceil() as usize;

        for step in 0..=step_count {
            let t = step as f64 * time_step;
            let fraction = t / total_time;
            let position = Vector3 {
                x: start.x + fraction * dx,
                y: start.y + fraction * dy,
                z: start.z + fraction * dz,
            };

            let state = create_vehicle_state(
                position,
                orientation,
                velocity_vector,
                &prev_state,
                time_step,
            );

            trajectory.push((stamp, state.clone()));
            prev_state = Some(state);
            increment_stamp(&mut stamp, time_step);
        }
    }

    Ok(trajectory)
}

fn create_vehicle_state(
    position: Vector3,
    orientation: Quaternion,
    velocity: Vector3,
    prev_state: &Option<VehicleState>,
    delta: f64,
) -> VehicleState {
    let (angular_velocity, angular_acceleration, acceleration) = if let Some(prev) = prev_state {
        calculate_dynamics(&orientation, &velocity, prev, delta)
    } else {
        (
            Vector3::new(0.0, 0.0, 0.0),
            Vector3::new(0.0, 0.0, 0.0),
            Vector3::new(0.0, 0.0, 0.0),
        )
    };

    let pose = Pose {
        position,
        orientation,
    };

    VehicleState {
        state: ActorState { pose },
        velocity: velocity,
        angular_velocity,
        acceleration,
        angular_acceleration,
    }
}

fn calculate_dynamics(
    orientation: &Quaternion,
    velocity_vector: &Vector3,
    prev_state: &VehicleState,
    delta: f64,
) -> (Vector3, Vector3, Vector3) {
    let q_current = crate::math::quaternion::Quaternion::new(
        orientation.w,
        orientation.x,
        orientation.y,
        orientation.z,
    );

    let q_prev = crate::math::quaternion::Quaternion::new(
        prev_state.state.pose.orientation.w,
        prev_state.state.pose.orientation.x,
        prev_state.state.pose.orientation.y,
        prev_state.state.pose.orientation.z,
    );

    let delta_orientation =
        quaternion_core::mul(quaternion_core::conj(q_prev._quat), q_current._quat);

    let (axis, angle) = quaternion_core::to_axis_angle(delta_orientation);

    let angular_velocity = Vector3 {
        x: axis[0] * angle / delta,
        y: axis[1] * angle / delta,
        z: axis[2] * angle / delta,
    };

    let angular_acceleration = Vector3 {
        x: (angular_velocity.x - prev_state.angular_velocity.x) / delta,
        y: (angular_velocity.y - prev_state.angular_velocity.y) / delta,
        z: (angular_velocity.z - prev_state.angular_velocity.z) / delta,
    };

    let acceleration = Vector3 {
        x: (velocity_vector.x - prev_state.velocity.x) / delta,
        y: (velocity_vector.y - prev_state.velocity.y) / delta,
        z: (velocity_vector.z - prev_state.velocity.z) / delta,
    };

    (angular_velocity, angular_acceleration, acceleration)
}

fn calculate_curvature(prev: math::Vector3, current: math::Vector3, next: math::Vector3) -> f64 {
    let vec1 = math::Vector3 {
        x: current.x - prev.x,
        y: current.y - prev.y,
        z: current.z - prev.z,
    };
    let vec2 = math::Vector3 {
        x: next.x - current.x,
        y: next.y - current.y,
        z: next.z - current.z,
    };

    let cross = math::Vector3 {
        x: vec1.y * vec2.z - vec1.z * vec2.y,
        y: vec1.z * vec2.x - vec1.x * vec2.z,
        z: vec1.x * vec2.y - vec1.y * vec2.x,
    };

    let denominator = vec1.length() * vec2.length() * prev.distance(next);

    if denominator.abs() <= std::f64::EPSILON {
        return 0.0;
    }

    let curvature = cross.length() / denominator;
    let sign = if cross.dot(math::Vector3 {
        x: 0.0,
        y: 0.0,
        z: 1.0,
    }) >= 0.0
    {
        1.0
    } else {
        -1.0
    };

    curvature * sign
}

fn compute_rpy_with_level_roll(ned1: math::Vector3, ned2: math::Vector3) -> (f64, f64, f64) {
    let dx = ned2.x - ned1.x;
    let dy = ned2.y - ned1.y;
    let dz = ned2.z - ned1.z;

    let magnitude = (dx * dx + dy * dy + dz * dz).sqrt();
    let nx = dx / magnitude;
    let ny = dy / magnitude;
    let nz = dz / magnitude;

    let roll = 0.0;
    let pitch = (-nz).asin();
    let yaw = ny.atan2(nx);

    let pitch = if pitch.is_nan() { 0.0 } else { pitch };
    let yaw = if yaw.is_nan() { 0.0 } else { yaw };

    (roll, pitch, yaw)
}

fn increment_stamp(stamp: &mut TimeStamp, delta: f64) {
    stamp.sec += delta.trunc() as i32;
    stamp.nanosec += (delta.fract() * 1.0e9) as u32;
    if stamp.nanosec >= 1_000_000_000u32 {
        stamp.nanosec -= 1_000_000_000u32;
        stamp.sec += 1;
    }
}

fn slerp(
    q1: crate::math::quaternion::Quaternion,
    q2: crate::math::quaternion::Quaternion,
    t: f64,
) -> crate::math::quaternion::Quaternion {
    let dot = q1.dot(q2).clamp(-1.0, 1.0);
    let q2 = if dot < 0.0 {
        crate::math::quaternion::Quaternion::new(-q2.w(), -q2.x(), -q2.y(), -q2.z())
    } else {
        q2
    };
    let dot = dot.abs();

    if dot.abs() > 0.9995 {
        return crate::math::quaternion::Quaternion::new(
            q1.w() + t * (q2.w() - q1.w()),
            q1.x() + t * (q2.x() - q1.x()),
            q1.y() + t * (q2.y() - q1.y()),
            q1.z() + t * (q2.z() - q1.z()),
        )
        .normalize();
    }

    let theta_0 = dot.acos();
    let theta = theta_0 * t;
    let sin_theta = theta.sin();
    let sin_theta_0 = theta_0.sin();

    let s1 = (theta_0 - theta).sin() / sin_theta_0;
    let s2 = sin_theta / sin_theta_0;

    crate::math::quaternion::Quaternion::new(
        s1 * q1.w() + s2 * q2.w(),
        s1 * q1.x() + s2 * q2.x(),
        s1 * q1.y() + s2 * q2.y(),
        s1 * q1.z() + s2 * q2.z(),
    )
}

#[derive(Debug, Serialize, Deserialize)]
struct TrajectoryPointRecord {
    time: f64,
    lat: f64,
    lon: f64,
    alt: f64,
}

impl TrajectoryPointRecord {
    fn from_csv_record(
        record: &csv::StringRecord,
        time_csv_column: usize,
        latitude_csv_column: usize,
        longitude_csv_column: usize,
        altitude_csv_column: usize,
        altitude_type: &str,
        time_type: &str,
    ) -> Result<Self, Box<dyn Error>> {
        let lat = record[latitude_csv_column].parse::<f64>()?;
        let lon = record[longitude_csv_column].parse::<f64>()?;

        let alt = match altitude_type.to_ascii_uppercase().as_str() {
            "MSL" => {
                let alt = record[altitude_csv_column].parse::<f64>()?;
                conversion_utils::msl_to_hae(lat, lon, alt, &Geoid::egm08())
            }
            "AGL" => unimplemented!("AGL is not supported yet"),
            "WGS84" => record[altitude_csv_column].parse::<f64>()?,
            _ => {
                return Err("Invalid altitude type".into());
            }
        };

        let time = match time_type.to_ascii_uppercase().as_str() {
            "ISO8601" => {
                let dt = record[time_csv_column].parse::<DateTime<Utc>>()?;
                dt.timestamp() as f64 + dt.timestamp_subsec_nanos() as f64 * 1e-9
            }
            "UNIX" => record[time_csv_column].parse::<f64>()?,
            _ => {
                return Err("Invalid time type".into());
            }
        };

        Ok(Self {
            time,
            lat,
            lon,
            alt,
        })
    }
}

#[pyfunction]
#[pyo3(signature = (
    csv_filepath,
    out_dir,
    time_csv_column,
    latitude_csv_column,
    longitude_csv_column,
    altitude_csv_column,
    altitude_type,
    time_type,
    id_csv_column=None,
    filter_id=None
))]
pub fn generate_trajectory_from_adsb_csv(
    csv_filepath: &str,
    out_dir: &str,
    time_csv_column: usize,
    latitude_csv_column: usize,
    longitude_csv_column: usize,
    altitude_csv_column: usize,
    altitude_type: &str,
    time_type: &str,
    id_csv_column: Option<usize>,
    filter_id: Option<&str>,
) -> PyResult<()> {
    let file = File::open(csv_filepath)?;
    let mut reader = Reader::from_reader(file);

    let mut single_trajectory = Vec::new();
    let mut id_map: HashMap<String, Vec<TrajectoryPointRecord>> = HashMap::new();

    for record_result in reader.records() {
        let record =
            record_result.map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let point = TrajectoryPointRecord::from_csv_record(
            &record,
            time_csv_column,
            latitude_csv_column,
            longitude_csv_column,
            altitude_csv_column,
            altitude_type,
            time_type,
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        if let Some(id_col) = id_csv_column {
            let csv_id_value = &record[id_col];
            if let Some(f_id) = filter_id {
                if csv_id_value != f_id {
                    continue;
                }
            }
            id_map
                .entry(csv_id_value.to_string())
                .or_insert_with(Vec::new)
                .push(point);
        } else {
            single_trajectory.push(point);
        }
    }

    fn shift_times_to_zero(points: &mut [TrajectoryPointRecord]) {
        if points.is_empty() {
            return;
        }
        let min_t = points.iter().map(|p| p.time).fold(f64::INFINITY, f64::min);
        for p in points {
            p.time -= min_t;
        }
    }

    let output_path = std::path::Path::new(out_dir);
    std::fs::create_dir_all(&output_path).map_err(|e| {
        pyo3::exceptions::PyIOError::new_err(format!("Cannot create output directory: {}", e))
    })?;

    if id_csv_column.is_none() {
        shift_times_to_zero(&mut single_trajectory);

        let json_data = serde_json::to_string_pretty(&single_trajectory)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let out_file_path = output_path.join("generated_trajectory.json");
        let mut out_file = File::create(&out_file_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        out_file
            .write_all(json_data.as_bytes())
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    } else {
        if let Some(f_id) = filter_id {
            if let Some(points_for_id) = id_map.get_mut(f_id) {
                shift_times_to_zero(points_for_id);
                let json_data = serde_json::to_string_pretty(&points_for_id)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                let filename = format!("{}_generated_trajectory.json", f_id);
                let out_file_path = output_path.join(&filename);

                let mut out_file = File::create(&out_file_path)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                out_file
                    .write_all(json_data.as_bytes())
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
            } else {
                log::error!(
                    "No records found for filter_id '{}', no file was generated.",
                    f_id
                );
            }
        } else {
            for (id_key, points_for_id) in id_map.iter_mut() {
                shift_times_to_zero(points_for_id);
                let json_data = serde_json::to_string_pretty(&points_for_id)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                let filename = format!("{}_generated_trajectory.json", id_key);
                let out_file_path = output_path.join(&filename);

                let mut out_file = File::create(&out_file_path)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
                out_file
                    .write_all(json_data.as_bytes())
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
            }
        }
    }

    Ok(())
}
