# Messages and data types

This page documents the message and data type structures for the topics used by the components of AeroSim to exchange data. See the [aerosim-data](https://github.com/aerosim-open/aerosim/tree/main/aerosim-data) module for more information.

* [ActorState](#actorstate)
* [AirCraftEffectorCommand](#aircrafteffectorcommand)
* [AutopilotCommand](#autopilotcommand)
* [CompressedImage](#compressedimage)
* [FlightControlCommand](#flightcontrolcommand)
* [Pose](#pose)
* [TimeStamp](#timestamp)
* [VehicleState](#vehiclestate)

---

## ActorState

Data type with generic actor information.

Fields:

* `pose`: `Pose` - Actor pose

---

## AirCraftEffectorCommand

Fields:

* `throttle_cmd`: *Vec&lt;f64&gt;* - engine throttle command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `aileron_cmd_angle_rad`: *Vec&lt;f64&gt;* - aileron deflection command in radians.
* `elevator_cmd_angle_rad`: *Vec&lt;f64&gt;* - elevator deflection command in radians..
* `rudder_cmd_angle_rad`: *Vec&lt;f64&gt;* - rudder deflection command in radians..
* `thrust_tilt_cmd_angle_rad`: *Vec&lt;f64&gt;* - thrust tilt command in radians..
* `flap_cmd_angle_rad`: *Vec&lt;f64&gt;* -  flap angle in radians.
* `speedbrake_cmd_angle_rad`: *Vec&lt;f64&gt;* - speedbrake angle in radians
* `landing_gear_cmd`: *Vec&lt;f64&gt;* - landing gear, 0.0 stowed, 1.0 deployed
* `wheel_steer_cmd_angle_rad`: *Vec&lt;f64&gt;* - wheel steer angle radians
* `wheel_brake_cmd`: *Vec&lt;f64&gt;* - wheel brake command, 1.0 fully applied, 0.0 no brake

---

## AutopilotCommand

* `flight_plan`: *String*
* `flight_plan_command`: *AutopilotFlightPlanCommand*
* `use_manual_setpoints`: *bool*
* `attitude_hold`: *bool* - True (hold altitude) or False
* `altitude_setpoint_ft`: *f64* - target hold altitude
* `airspeed_hold`: *bool* - True (hold airspeed) or False
* `airspeed_setpoint_kts`: *f64* - target hold airspeed
* `heading_hold`: *bool* - True (hold heading) or False
* `heading_set_by_waypoint`: *bool* - True (use waypoint) or False
* `heading_setpoint_deg`: *f64* - target heading in degrees
* `target_wp_latitude_deg`: *f64* - target waypoint latitude
* `target_wp_longitude_deg`: *f64* - target waypoint longitude

---

## CompressedImage

Data type enconding images from rendered with compression.

Fields:

* `header`: *aerosim_data/msg/Header* - Message header with timeStamp and frame ID information
* `height`: *uint32* - Height of the image 
* `width`: *uint32* - Width of the image
* `format`: *string* - Format of the image
* `data`: *sequence<uint8>* - Image data as a sequence of integers

---

## FlightControlCommand

Data type used as input to a flight controller, got as output from (auto)pilot.

Fields:

* `power_cmd`: *Vec&lt;f64&gt;* - vehicle power command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices.
* `roll_cmd`: *f64* - vehicle roll command. Scales between -1.0 and 1.0
* `pitch_cmd`: *f64* - vehicle pitch command. Scales between -1.0 and 1.0
* `yaw_cmd`: *f64* - vehicle yaw command. Scales between -1.0 and 1.0
* `thrust_tilt_cmd`: *f64* - tilt command for a tilt-rotor craft. Scales between 0.0 and 1.0
* `flap_cmd`: *f64* - flap state command. Scales between 0.0 and 1.0
* `speedbrake_cmd`: *f64* - speed brake command. Scales between 0.0 and 1.0
* `landing_gear_cmd`: *f64* - landing gear command. Scales between 0.0 (stowed) amd 1.0 (extended)
* `wheel_steer_cmd`: *f64* - wheel steer for taxi. Scales between -1.0 (left) and 1.0 (right)
* `wheel_brake_cmd`: *f64* - wheel brake command. Scales between 0.0 (off) and 1.0 (full strength)

---

## Pose

Data type with position and orientation information of an actor.

Fields:

* `position`: `Vector3` - Actor 3D position
* `orientation`: `Quaternion` - Actor quaternion orientation

---

## TimeStamp

Data type containing a simulator time stamp.

Fields:

* `sec`: *int32* - simulation time in seconds
* `nanosec`: *uint32* - simulation time in nanoseconds beyond the given time in seconds

---

## VehicleState

Data type containing information about the vehicle state, including pose, velocity and acceleration and angular velocity/acceleration.

Fields:

* `state`: *ActorState* - combined actor state information
    * `pose`: *Pose* - actor pose
        * `header`: *Header* - header containing ancilliary information
            * `stamp`: *TimeStamp*
                * `sec`: *int32*
                * `nanosec`: *uint32*
            * `frame_id`: *String* - simulation frame ID
        * `position`: *Vector3* - position in meters
            * `x`, `y`, `z`
        * `orientation`: *Quaternion* - orientation, using quaternion notation
            * `w`, `x`, `y`, `z`
* `velocity`: *Vector3* actor velocity in m/s
    * `x`, `y`, `z`
* `angular_velocity`: *Vector3* - actor angular velocity in rad/s
    * `x`, `y`, `z`
* `acceleration`: *Vector3* - actor acceleration in m/s<sup>2</sup>
    * `x`, `y`, `z`
* `angular_acceleration`: *Vector3* - actor angular acceleration in rad/s<sup>2</sup>
    * `x`, `y`, `z`
