# Messages and data types

This page documents the message and data type structures for the topics used by the components of AeroSim to exchange data. See the [aerosim-data](https://github.com/aerosim-open/aerosim/tree/main/aerosim-data) module for more information.

* [ActorModel](#actormodel)
* [ActorState](#actorstate)
* [AircraftEffectorCommand](#aircrafteffectorcommand)
* [AutopilotCommand](#autopilotcommand)
* [AutopilotFlightPlanCommand](#autopilotflightplancommand)
* [CameraInfo](#camerainfo)
* [CompressedImage](#compressedimage)
* [EffectorState](#effectorstate)
* [FlightControlCommand](#flightcontrolcommand)
* [GNSS](#gnss)
* [Header](#header)
* [HSIMode](#hsimode)
* [Image](#image)
* [ImageEncoding](#imageencoding)
* [ImageFormat](#imageformat)
* [IMU](#imu)
* [JsonData](#jsondata)
* [PhysicalProperties](#physicalproperties)
* [Pose](#pose)
* [PrimaryFlightDisplayData](#primaryflightdisplaydata)
* [Quaternion](#quaternion)
* [TimeStamp](#timestamp)
* [TrajectoryVisualization](#trajectoryvisualization)
* [TrajectoryVisualizationSettings](#trajectoryvisualizationsettings)
* [TrajectoryWaypoints](#trajectorywaypoints)
* [Vector3](#vector3)
* [VehicleState](#vehiclestate)

---

## ActorModel

Data type specifying the asset and physical properties of an actor.

Fields:

* `physical_properties`: [`PhysicalProperties`](#physicalproperties) - Physical properties of the actor.
* `asset_link`: `Option<String>` - Link to the asset of the actor.

---

## ActorState

Data type with generic actor information.

Fields:

* `pose`: [`Pose`](#pose) - Actor pose.

---

## AircraftEffectorCommand

Data type with input to flight dynamics model, output from flight controller.

Fields:

* `throttle_cmd`: `Vec<f64>` - Engine throttle command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `aileron_cmd_angle_rad`: `Vec<f64>` - Aileron deflection command in radians.
* `elevator_cmd_angle_rad`: `Vec<f64>` - Elevator deflection command in radians.
* `rudder_cmd_angle_rad`: `Vec<f64>` - Rudder deflection command in radians.
* `thrust_tilt_cmd_angle_rad`: `Vec<f64>` - Thrust tilt command in radians.
* `flap_cmd_angle_rad`: `Vec<f64>` -  Flap angle in radians.
* `speedbrake_cmd_angle_rad`: `Vec<f64>` - Speedbrake angle in radians.
* `landing_gear_cmd`: `Vec<f64>` - Landing gear, 0.0 stowed, 1.0 deployed.
* `wheel_steer_cmd_angle_rad`: `Vec<f64>` - Wheel steer angle radians.
* `wheel_brake_cmd`: `Vec<f64>` - Wheel brake command, 1.0 fully applied, 0.0 no brake.

---

## AutopilotCommand

Input to autopilot.

Fields:

* `flight_plan`: `String` - Flight plan information, e.g. waypoints, mission, etc.
* `flight_plan_command`: [`AutopilotFlightPlanCommand`](#autopilotflightplancommand) - Flight plan execution command: `Stop`, `Run` or `Pause`.
* `use_manual_setpoints`: `bool` - Flag to use manual setpoints instead of flight plan.
* `attitude_hold`: `bool` - Flag to hold current attitude roll/pitch/yaw if True.
* `altitude_setpoint_ft`: `f64` - Target hold altitude in feet.
* `airspeed_hold`: `bool` - Flag to hold airspeed if True.
* `airspeed_setpoint_kts`: `f64` - Target hold airspeed in knots.
* `heading_hold`: `bool` - Flag to hold heading if True.
* `heading_set_by_waypoint`: `bool` - Flag to use waypoint as target heading instead of heading_setpoint if True.
* `heading_setpoint_deg`: `f64` - Target heading setpoint in degrees (0 = north, 90 = east, 180 = south, 270 = west).
* `target_wp_latitude_deg`: `f64` - Target waypoint latitude in degrees.
* `target_wp_longitude_deg`: `f64` - Target waypoint longitude in degrees.

---

## AutopilotFlightPlanCommand

Enum with the different commands for the autopilot flight plan.

Fields:

- `Stop` = 0
- `Run` = 1
- `Pause` = 2

---

## CameraInfo

Data type with information about the camera settings.

Fields:

* `width`: `u32` - Width of the camera.
* `height`: `u32` - Height of the camera.
* `distortion_model`: `String` - Distortion model assumed in the camera.
* `d`: `Vec<f64>` - Camera parameter *d*.
* `k`: `[f64; 9]` - Camera parameter *k*.
* `r`: `[f64; 9]` - Camera parameter *r*.
* `p`: `[f64; 12]` - Camera parameter *p*.

---

## CompressedImage

Compressed images from the [`Image`](#image) data type using [turbojpeg](https://docs.rs/turbojpeg/latest/turbojpeg/) via the method `compress`. Can be decompress to an [`Image`](#image) type through the `decompress` method. Dimensions of the image are encoded in the compression.

Fields:

* `format`: [`ImageFormat`](#imageformat) - Format of the image, either `JPEG` or `PNG`.
* `data`: `Vec<u8>` - Image data.

---

## EffectorState

Data type with effector state information, used in the FMU models definition.

Fields:

* `pose`: [`Pose`](#pose) - Actor pose.

---

## FlightControlCommand

Data type used as input to a flight controller, got as output from (auto)pilot.

Fields:

* `power_cmd`: `Vec<f64>` - Vehicle power command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `roll_cmd`: `f64` - Vehicle roll command. Scales between -1.0 and 1.0.
* `pitch_cmd`: `f64` - Vehicle pitch command. Scales between -1.0 and 1.0.
* `yaw_cmd`: `f64` - Vehicle yaw command. Scales between -1.0 and 1.0.
* `thrust_tilt_cmd`: `f64` - Tilt command for a tilt-rotor craft. Scales between 0.0 and 1.0.
* `flap_cmd`: `f64` - Flap state command. Scales between 0.0 and 1.0.
* `speedbrake_cmd`: `f64` - Speed brake command. Scales between 0.0 and 1.0.
* `landing_gear_cmd`: `f64` - Landing gear command. Scales between 0.0 (stowed) amd 1.0 (extended).
* `wheel_steer_cmd`: `f64` - Wheel steer for taxi. Scales between -1.0 (left) and 1.0 (right).
* `wheel_brake_cmd`: `f64` - Wheel brake command. Scales between 0.0 (off) and 1.0 (full strength).

---

## GNSS

GNSS message.

Fields:

* `latitude`: `f64` - Data latitude.
* `longitude`: `f64` - Data longitude.
* `altitude`: `f64` - Data altitude.
* `velocity`: [`Vector3`](#vector3) - 3D velocity.
* `heading`: `f64` - Heading.

---

## Header

Header present in all messages.

Fields:

* `timestamp_sim`: [`TimeStamp`](#timestamp) - Discrete simulation time. A sentinel value `{sec: i32::MIN, nanosec: 0}` is set when the simulation time is not specified.
* `timestamp_platform`: [`TimeStamp`](#timestamp) - Absolute platform time since the Unix Epoch.
* `frame_id`: `String` - Identifier for the frame.

---

## HSIMode

Enum with different available HSI modes for the [`PrimaryFlightDisplayData`](#primaryflightdisplaydata).

Fields:

- `GPS` = 0
- `VOR1` = 1
- `VOR2` = 2

---

## Image

Data type for encoding images. Can be converted through the `compress` method to a [`CompressedImage`](#compressedimage).

Fields:

* `camera_info`: [`CameraInfo`](#camerainfo) - Information of the camera source.
* `height`: `u32` - Height of the image.
* `width`: `u32` - Width of the image.
* `encoding`: [`ImageEncoding`](#imageencoding) - Type of enconding of the image.
* `is_bigendian`: `u8` - Whether it is big endian or not (order of bytes encoding).
* `step`: `u32`
* `data`: `Vec<u8>` - Image data as a sequence of integers.

---

## ImageEncoding

Enunm with image encoding available options.

Fields:

- `RGB8`
- `RGBA8`
- `BGR8`
- `BGRA8`
- `MONO8`
- `MONO16`
- `YUV422`

---

## ImageFormat

Enum indicating the format of a [`CompressedImage`](#compressedimage).

Fields:

- `JPEG`
- `PNG`

---

## IMU

IMU sensor messages.

Fields:

* `acceleration`: [`Vector3`](#vector3) - Acceleration data.
* `gyroscope`: [`Vector3`](#vector3) - Gyroscope data, with angular velocity information.
* `magnetic_field`: [`Vector3`](#vector3) - Magnetic field data.

---

## JsonData

Generic data type to encode json data.

Fields:

* `data`: `String` - data to be encoded as json.

---

## PhysicalProperties

Physical properties of an actor.

Fields:

* `mass`: `f64` - Mass of the actor.
* `inertia_tensor`: [`Vector3`](#vector3) - Inertia tensor of the actor, indicated as a vector.
* `moment_of_inertia`: [`Vector3`](#vector3) - Moment of inertia of the actor.

---

## Pose

Data type with position and orientation information of an actor.

Fields:

* `position`: [`Vector3`](#vector3) - Actor 3D position.
* `orientation`: [`Quaternion`](#quaternion) - Actor quaternion orientation.

---

## PrimaryFlightDisplayData

Flight data to be displayed in the deck's Primary Flight Display (PFD) component.

Fields:

* `airspeed_kts`: `f64` - JSBSim `velocities/vc-kts`.
* `true_airspeed_kts`: `f64` - JSBSim `velocities/vtrue-kts`.
* `altitude_ft`: `f64` - JSBSim `position/h-sl-ft`.
* `target_altitude_ft`: `f64` - AutopilotCommand `altitude_setpoint_ft`.
* `altimeter_pressure_setting_inhg`: `f64` - User-set value (standard pressure = 29.92 inHG, QNH = height above MSL adjusted from local atmospheric pressure, QFE = height above airfield elevation).
* `vertical_speed_fpm`: `f64` - JSBSim `velocities/h-dot-fps` converted to feet/min.
* `pitch_deg`: `f64` - JSBSim `attitude/pitch-rad`.
* `roll_deg`: `f64` - JSBSim `attitude/roll-rad`.
* `side_slip_fps2`: `f64` - JSBSim `accelerations/vdot-ft_sec2`.
* `heading_deg`: `f64` - JSBSim `attitude/heading-true-rad` converted to deg.
* `hsi_course_select_heading_deg`: `f64` - For GPS mode, calculated heading between prev and next waypoints.
* `hsi_course_deviation_deg`: `f64` - For GPS mode, nautical mile offset from course line converted as 5 NM = 12 deg.
* `hsi_mode`: [`HSIMode`](#hsimode) - User-set mode, start with GPS only. Available options: `GPS`, `VOR1` and `VOR2`.

---

## Quaternion

Quaternion data type.

* `w`: `f64` - Scalar component.
* `x`: `f64` - x coordinate.
* `y`: `f64` - y coordinate.
* `z`: `f64` - z coordinate.

---

## TimeStamp

Data type containing a simulator time stamp.

Fields:

* `sec`: `int32` - Simulation time in seconds.
* `nanosec`: `uint32` - Simulation time in nanoseconds beyond the given time in seconds.

---

## TrajectoryVisualization

Aircraft Trajectory Visualization Command.

Fields:

* `settings`: [`TrajectoryVisualizationSettings`](#trajectoryvisualizationsettings) - Settings of the trajectory visualization.
* `user_defined_waypoints`: [`TrajectoryWaypoints`](#trajectorywaypoints) - User defined waypoints.
* `future_trajectory`: [`TrajectoryWaypoints`](#trajectorywaypoints) - Future waypoints of the trajectory.

---

## TrajectoryVisualizationSettings

Settings fot the [`TrajectoryVisualization`](#trajectoryvisualization) messages.

Fields:

* `display_future_trajectory`: `bool` - Whether to display future trajectory points.
* `display_past_trajectory`: `bool` - Whether to display past trajectory points.
* `highlight_user_defined_waypoints`: `bool` - Whether to highlight those waypoints set by the user.
* `number_of_future_waypoints`: `u64` - Indicates the number of waypoints in the future trajectory.
---

## TrajectoryWaypoints

Indicate the waypoints of a trajectory by a string.

Fields:

* `waypoints`: `String` - string with waypoints of the trajectory.

---

## Vector3

Generic vector 3D data type.

* `x`: `f64` - x coordinate.
* `y`: `f64` - y coordinate.
* `z`: `f64` - z coordinate.

---

## VehicleState

Data type containing information about the vehicle state, including pose, velocity and acceleration and angular velocity/acceleration.

Fields:

* `state`: [`ActorState`](#actorstate) - Combined actor state information.
* `velocity`: [`Vector3`](#vector3) - Actor velocity in m/s.
* `angular_velocity`: [`Vector3`](#vector3) - Actor angular velocity in rad/s.
* `acceleration`: [`Vector3`](#vector3) - Actor acceleration in m/s<sup>2</sup>.
* `angular_acceleration`: [`Vector3`](#vector3) - Actor angular acceleration in rad/s<sup>2</sup>.
