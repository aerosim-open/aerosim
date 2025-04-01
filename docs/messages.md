# Messages

This page documents the message structures for the topics used by the components of AeroSim to exchange data. 

* [TimeStamp](#timestamp)
* [VehicleState](#vehiclestate)
* [FlightControlCommand](#flightcontrolcommand)
* [AirCraftEffectorCommand](#aircrafteffectorcommand)
* [AutopilotCommand](#autopilotcommand)
* [AutopilotFlightPlanCommand](#autopilotflightplancommand)

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

---

## FlightControlCommand

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

## AirCraftEffectorCommand

Fields:

* `throttle_cmd`: *Vec&lt;f64&gt;* - engine throttle command. Scales between 0.0 (no power) and 1.0 (max power). Values are provided in an array for multiple thrust-generating devices. 
* `aileron_cmd_angle_rad`: *Vec&lt;f64&gt;* - aileron deflection command in radians. 
* `elevator_cmd_angle_rad`: *Vec&lt;f64&gt;* - elevator deflection command in radians..
* `rudder_cmd_angle_rad`: *Vec&lt;f64&gt;* - rudder deflection command in radians..
* `thrust_tilt_cmd_angle_rad`: *Vec&lt;f64&gt;* - thrust tilt command in radians.. 
* `flap_cmd_angle_rad`: *Vec&lt;f64&gt;* -  flap angle in radians.
* `speedbrake_cmd_angle_rad`: *Vec&lt;f64&gt;* - 
* `landing_gear_cmd`: *Vec&lt;f64&gt;* - 
* `wheel_steer_cmd_angle_rad`: *Vec&lt;f64&gt;* - 
* `wheel_brake_cmd`: *Vec&lt;f64&gt;* - 

---

## AutopilotCommand

* `flight_plan`: *String*
* `flight_plan_command`: *AutopilotFlightPlanCommand*
* `use_manual_setpoints`: *bool*
* `attitude_hold`: *bool* - True (hold altitude) or False
* `altitude_hold`: *bool*
* `altitude_setpoint_ft`: *f64*
* `airspeed_hold`: *bool*
* `airspeed_setpoint_kts`: *f64*
* `heading_hold`: *bool*
* `heading_set_by_waypoint`: *bool*
* `heading_setpoint_deg`: *f64*
* `target_wp_latitude_deg`: *f64*
* `target_wp_longitude_deg`: *f64*

---

## AutopilotFlightPlanCommand

* `Stop` = 0
* `Run` = 1
* `Pause` = 2