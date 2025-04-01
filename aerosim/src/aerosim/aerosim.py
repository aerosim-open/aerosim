import json
import os
import time

# AeroSim packages
import aerosim_world
from aerosim_data import middleware
from aerosim_data import types as aerosim_types


class AeroSim:
    def __init__(self) -> None:
        self.sim_config_json = None
        self.aerosim_orchestrator = None
        self.aerosim_fmudrivers = []
        self.is_sim_started = False
        self.simclock_msg = None
        self.transport = middleware.get_transport("kafka")

    def run(
        self,
        sim_config_file: str,
        sim_config_dir: str = os.getcwd(),
        wait_for_sim_start: bool = True,
    ):
        # ----------------------------------------------
        # Load the sim configuration
        sim_config_path = os.path.abspath(os.path.join(sim_config_dir, sim_config_file))
        print(f"Loading simulation configuration from {sim_config_path}...")
        with open(sim_config_path, "r") as file:
            self.sim_config_json = json.load(file)

        # print("Simulation configuration loaded:")
        # print(json.dumps(self.sim_config_json, indent=4))

        # ----------------------------------------------
        # Initialize AeroSim components

        print("Initializing AeroSim Orchestrator...")
        self.aerosim_orchestrator = aerosim_world.Orchestrator()
        self.transport.subscribe(
            aerosim_types.JsonData,
            "aerosim.clock",
            self.on_sim_clock_step,
        )

        for fmu_config in self.sim_config_json["fmu_models"]:
            print(f"Initializing AeroSim FMU Driver '{fmu_config['id']}'...")
            self.aerosim_fmudrivers.append(
                aerosim_world.FmuDriver(fmu_config["id"], sim_config_dir)
            )

        # ----------------------------------------------
        # Load AeroSim components

        # Load orchestrator first because it creates the topics
        print("Loading AeroSim Orchestrator...")
        try:
            self.aerosim_orchestrator.load(json.dumps(self.sim_config_json))
        except Exception as exc:
            print(f"Error loading AeroSim Orchestrator: {exc}")
            raise exc

        # ----------------------------------------------
        # Start AeroSim components

        for fmu_driver in self.aerosim_fmudrivers:
            print(f"Starting AeroSim FMU Driver '{fmu_driver.fmu_id}'...")
            fmu_driver.start()

        print("Starting AeroSim Orchestrator...")
        try:
            self.aerosim_orchestrator.start()
            if wait_for_sim_start:
                start_timeout_sec = 60
                start_time = time.time()
                while not self.is_sim_started:
                    if time.time() - start_time > start_timeout_sec:
                        raise TimeoutError(
                            f"Simulation did not start after {start_timeout_sec} seconds."
                        )
                    time.sleep(0.1)
        except KeyboardInterrupt as exc:
            print("KeyboardInterrupt: Stopping simulation...")
            self.stop()
            raise exc
        except Exception as exc:
            print(f"Error starting AeroSim Orchestrator: {exc}")
            raise exc

    def stop(self):
        self.aerosim_orchestrator.stop()
        for fmu_driver in self.aerosim_fmudrivers:
            fmu_driver.stop()
        print("Finished.")

    def on_sim_clock_step(self, data, _):
        self.is_sim_started = True
        self.simclock_msg = data

    def get_sim_time(self) -> dict | None:
        if self.simclock_msg is None:
            return None
        else:
            return self.simclock_msg["timestamp_sim"]
