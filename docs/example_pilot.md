# Pilot Control with Flight Deck Example

This example demonstrates how to run a simulation to fly an airplane with a
flight deck in three modes:

1. Joystick direct control of flight control surfaces (Xbox controller mapping)
2. Keyboard control of autopilot setpoints (airspeed, altitude, heading)
3. Autopilot control by flight plan waypoints (example_flight_plan.json)

To run it, in the AeroSim directory run:

```sh
cd examples
python pilot_control_with_flight_deck.py
```

Enter `1`, `2`, or `3` to choose the control mode from the options listed above.
Use keyboard or joystick inputs with the AeroSim App window active:
    
- For mode 1 using an Xbox controller
    - "Y" button increases power (sets throttle to 100%)
    - "A" button decreases power (sets throttle to 0%)
    - Left stick controls roll and pitch
    - Right stick controls yaw

- For mode 2 using the keyboard
    - "Up arrow" key increases airspeed setpoint (non-zero setpoint sets throttle to 100%)
    - "Down arrow" key decreases airspeed setpoint (zero setpoint sets throttle to 0%)
    - "W" key increases altitude setpoint (ascend)
    - "S" key decreases altitude setpoint (descend)
    - "A" key decreases heading setpoint (turn left)
    - "D" key increases heading setpoint (turn right)
    
- For mode 3 using the keyboard
    - Autopilot control automatically flies the flight plan waypoints specified in example_flight_plan.json
    - No keyboard/joystick control

Ctrl-C breaks the script to stop the simulation.