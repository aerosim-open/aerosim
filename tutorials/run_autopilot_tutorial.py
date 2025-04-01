from aerosim import AeroSim

# --------------------------------------------
# Set path to configuration file

json_config_file = "config/sim_config_autopilot_tutorial.json"

# --------------------------------------------
# Run AeroSim simulation

aerosim = AeroSim()
aerosim.run(json_config_file)

# --------------------------------------------
# Let the simulation run

try:
    input("Simulation is running. Press any key to stop...")
except KeyboardInterrupt:
    print("Simulation stopped.")
finally:
    # --------------------------------------------
    # Stop AeroSim simulation
    aerosim.stop()