"""
Core simulation class for AeroSim.

This module contains the enhanced AeroSim class that provides the main simulation functionality.
"""

import os
import json
import asyncio
import time

# AeroSim packages
import aerosim_world
from aerosim_data import middleware
from aerosim_data import types as aerosim_types

class AeroSim:
    """
    Enhanced AeroSim simulation class.

    This class provides the core simulation functionality with improved support for
    WebSockets, input handling, and visualization.
    """

    def __init__(self, enable_websockets: bool = False) -> None:
        """
        Initialize the AeroSim simulation.

        Args:
            enable_websockets: Whether to enable WebSockets support for communication with aerosim-app
        """
        self.sim_config_json = None
        self.aerosim_orchestrator = None
        self.aerosim_fmudrivers = []
        self.enable_websockets = enable_websockets
        self.websocket_tasks = []
        self.is_sim_started = False
        self.simclock_msg = None
        self.transport = middleware.get_transport("kafka")

    def run(self, sim_config_file: str, sim_config_dir: str = os.getcwd(), wait_for_sim_start: bool = True) -> None:
        """
        Run the AeroSim simulation.

        Args:
            sim_config_file: Path to the simulation configuration file
            sim_config_dir: Directory containing the simulation configuration file
            wait_for_sim_start: Whether to wait for the simulation to start before returning
        """
        # ----------------------------------------------
        # Load the sim configuration
        sim_config_path = os.path.abspath(os.path.join(sim_config_dir, sim_config_file))
        print(f"Loading simulation configuration from {sim_config_path}...")
        with open(sim_config_path, "r") as file:
            self.sim_config_json = json.load(file)

        # ----------------------------------------------
        # Initialize AeroSim components
        print("Initializing AeroSim Orchestrator...")
        self.aerosim_orchestrator = aerosim_world.Orchestrator()

        # Subscribe to simulation clock for tracking simulation start and time
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

    async def run_with_websockets(self, sim_config_file: str, sim_config_dir: str = os.getcwd(), wait_for_sim_start: bool = True) -> None:
        """
        Run the AeroSim simulation with WebSockets support.

        This method starts the simulation and WebSockets servers for communication with aerosim-app.

        Args:
            sim_config_file: Path to the simulation configuration file
            sim_config_dir: Directory containing the simulation configuration file
            wait_for_sim_start: Whether to wait for the simulation to start before returning
        """
        from ..io.websockets import start_websocket_servers

        # Start the simulation
        self.run(sim_config_file, sim_config_dir, wait_for_sim_start)

        if self.enable_websockets:
            # Start WebSockets servers
            print("Starting WebSockets servers...")
            self.websocket_tasks = await start_websocket_servers()

            # Wait for WebSockets servers to complete
            await asyncio.gather(*self.websocket_tasks)

    def stop(self) -> None:
        """
        Stop the AeroSim simulation.
        """
        if self.aerosim_orchestrator:
            self.aerosim_orchestrator.stop()

        for fmu_driver in self.aerosim_fmudrivers:
            fmu_driver.stop()

        # Cancel any WebSockets tasks
        for task in self.websocket_tasks:
            if not task.done():
                task.cancel()

        print("AeroSim simulation stopped.")

    def on_sim_clock_step(self, data, _) -> None:
        """
        Callback function for simulation clock updates.

        This is called whenever a new simulation clock message is received.

        Args:
            data: The simulation clock data
            _: Unused topic parameter
        """
        self.is_sim_started = True
        self.simclock_msg = data

    def get_sim_time(self) -> dict | None:
        """
        Get the current simulation time.

        Returns:
            The simulation timestamp or None if not available
        """
        if self.simclock_msg is None:
            return None
        else:
            return self.simclock_msg["timestamp_sim"]
