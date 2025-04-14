# Messages and data types

This page documents the message and data type structures for the topics used by the components of AeroSim to exchange data. See the [aerosim-data](https://github.com/aerosim-open/aerosim/tree/main/aerosim-data) module for more information.

* [ActorState](#actorstate)
* [AirCraftEffectorCommand](#aircrafteffectorcommand)
* [AutopilotCommand](#autopilotcommand)
* [CompressedImage](#compressedimage)
* [FlightControlCommand](#flightcontrolcommand)
* [Image](#image)
* [Pose](#pose)
* [Quaternion](#quaternion)
* [TimeStamp](#timestamp)
* [Vector3](#vector3)
* [VehicleState](#vehiclestate)

---

## ActorState

Data type with generic actor information.

Fields:

* `pose`: `Pose` - Actor pose

---

## AirCraftEffectorCommand

Fields:

* `throttle_cmd`: `Vec<f64>` - Engine throttle command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `aileron_cmd_angle_rad`: `Vec<f64>` - Aileron deflection command in radians.
* `elevator_cmd_angle_rad`: `Vec<f64>` - Elevator deflection command in radians..
* `rudder_cmd_angle_rad`: `Vec<f64>` - Rudder deflection command in radians..
* `thrust_tilt_cmd_angle_rad`: `Vec<f64>` - Thrust tilt command in radians..
* `flap_cmd_angle_rad`: `Vec<f64>` -  Flap angle in radians.
* `speedbrake_cmd_angle_rad`: `Vec<f64>` - Speedbrake angle in radians
* `landing_gear_cmd`: `Vec<f64>` - Landing gear, 0.0 stowed, 1.0 deployed
* `wheel_steer_cmd_angle_rad`: `Vec<f64>` - Wheel steer angle radians
* `wheel_brake_cmd`: `Vec<f64>` - Wheel brake command, 1.0 fully applied, 0.0 no brake

---

## AutopilotCommand

* `flight_plan`: `String` - Flight plan information, e.g. waypoints, mission, etc.
* `flight_plan_command`: `AutopilotFlightPlanCommand` - Flight plan execution command
* `use_manual_setpoints`: `bool` - Flag to use manual setpoints instead of flight plan
* `attitude_hold`: `bool` - Flag to hold current attitude roll/pitch/yaw if True
* `altitude_setpoint_ft`: `f64` - Target hold altitude in feet
* `airspeed_hold`: `bool` - Flag to hold airspeed if True
* `airspeed_setpoint_kts`: `f64` - Target hold airspeed in knots
* `heading_hold`: `bool` - Flag to hold heading if True
* `heading_set_by_waypoint`: `bool` - Flag to use waypoint as target heading instead of heading_setpoint if True
* `heading_setpoint_deg`: `f64` - Target heading setpoint in degrees (0 = north, 90 = east, 180 = south, 270 = west)
* `target_wp_latitude_deg`: `f64` - Target waypoint latitude in degrees
* `target_wp_longitude_deg`: `f64` - Target waypoint longitude in degrees

---

## CameraInfo

Data type with information about the camera settings.

Fields:

* `width`: `u32`
* `height`: `u32`
* `distortion_model`: `String`
* `d`: `Vec<f64>`
* `k`: `[f64; 9]`
* `r`: `[f64; 9]`
* `p`: `[f64; 12]`

---

## CompressedImage

Compressed images from the `Image` data type using [turbojpeg](https://docs.rs/turbojpeg/latest/turbojpeg/) via the method `compress`. Can be decompress to an `Image` type through the `decompress` method. Dimensions of the image are encoded in the compression.

Fields:

* `format`: `ImageFormat` - Format of the image, `JPEG` or `PNG`.
* `data`: `Vec<u8>` - Image data

---

## FlightControlCommand

Data type used as input to a flight controller, got as output from (auto)pilot.

Fields:

* `power_cmd`: `Vec<f64>` - Vehicle power command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `roll_cmd`: `f64` - Vehicle roll command. Scales between -1.0 and 1.0
* `pitch_cmd`: `f64` - Vehicle pitch command. Scales between -1.0 and 1.0
* `yaw_cmd`: `f64` - Vehicle yaw command. Scales between -1.0 and 1.0
* `thrust_tilt_cmd`: `f64` - Tilt command for a tilt-rotor craft. Scales between 0.0 and 1.0
* `flap_cmd`: `f64` - Flap state command. Scales between 0.0 and 1.0
* `speedbrake_cmd`: `f64` - Speed brake command. Scales between 0.0 and 1.0
* `landing_gear_cmd`: `f64` - Landing gear command. Scales between 0.0 (stowed) amd 1.0 (extended)
* `wheel_steer_cmd`: `f64` - Wheel steer for taxi. Scales between -1.0 (left) and 1.0 (right)
* `wheel_brake_cmd`: `f64` - Wheel brake command. Scales between 0.0 (off) and 1.0 (full strength)

---

## Image

Data type for encoding images. Can be converted through the `compress` method to a `CompressedImage`.

Fields:

* `camera_info`: `CameraInfo` - Information of the camera source
* `height`: `u32` - Height of the image
* `width`: `u32` - Width of the image 
* `encoding`: `ImageEncoding` - Type of enconding of the image:
    - `RGB8`
    - `RGBA8`
    - `BGR8`
    - `BGRA8`
    - `MONO8`
    - `MONO16`
    - `YUV422`
* `is_bigendian`: `u8` - Whether it is big endian or not (order of bytes encoding)
* `step`: `u32`
* `data`: `Vec<u8>` - Image data as a sequence of integers

---

## Pose

Data type with position and orientation information of an actor.

Fields:

* `position`: `Vector3` - Actor 3D position
* `orientation`: `Quaternion` - Actor quaternion orientation

---

## Quaternion

Quaternion data type.

* `w`: `f64` - Scalar component
* `x`: `f64` - x coordinate
* `y`: `f64` - y coordinate
* `z`: `f64` - z coordinate

---

## TimeStamp

Data type containing a simulator time stamp.

Fields:

* `sec`: `int32` - Simulation time in seconds
* `nanosec`: `uint32` - Simulation time in nanoseconds beyond the given time in seconds

---

## Vector3

Generic vector 3D data type

* `x`: `f64` - x coordinate
* `y`: `f64` - y coordinate
* `z`: `f64` - z coordinate

---

## VehicleState

Data type containing information about the vehicle state, including pose, velocity and acceleration and angular velocity/acceleration.

Fields:

* `state`: `ActorState` - Combined actor state information
* `velocity`: `Vector3` - Actor velocity in m/s
* `angular_velocity`: `Vector3` - Actor angular velocity in rad/s
* `acceleration`: `Vector3` - Actor acceleration in m/s<sup>2</sup>
* `angular_acceleration`: `Vector3` - Actor angular acceleration in rad/s<sup>2</sup>
