"""
Simulink Co-Simulation and FMU Example

This example demonstrates how to use the aerosim package to:
1. Run a simulation that co-simulates with Simulink
2. Stream camera images to aerosim-app

This example shows how to integrate AeroSim with Simulink models
for advanced control and simulation capabilities.

Usage:
    1. See the aerosim-simulink repo's README for how to build the AeroSim S-function
      MEX files. Then from the aerosim-simulink/examples/ directory, run the
      'load_aerosim_simulink_cosim_demo.m' script in MATLAB to load the example
      Simulink co-sim model.

    2. Launch AeroSim and start the selected renderer.

    3. Start the Simulink model (the Simulink clock will wait and not start stepping
      until the AeroSim simulation starts running).

    4. Run this script to start the AeroSim simulation. The Simulink model should start
      stepping in lock-step with the AeroSim simulation. You can control the altitude
      of the helicopter in the Simulink model using the altitude slider.

    Ctrl-C breaks the script to stop the simulation and then the Simulink model should
    automatically stop as well.
"""

import time
import threading
import traceback
import asyncio
import logging
import os

from aerosim import AeroSim
from aerosim_data import types as aerosim_types
from aerosim_data import middleware

# Import WebSocket server functionality
from aerosim.io.websockets import (
    start_websocket_servers,
    DEFAULT_COMMAND_PORT,
    DEFAULT_IMAGE_PORT,
    DEFAULT_DATA_PORT,
)
from aerosim.io.websockets.command_server import command_queue
from aerosim.io.websockets.image_server import on_camera_data
from aerosim.io.websockets.data_server import on_flight_display_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aerosim.simulink_cosim")

# --------------------------------------------
# Run AeroSim simulation
# --------------------------------------------
def run_simulation() -> None:
    """Run the AeroSim simulation with Simulink co-simulation"""
    try:
        # Get the script directory to handle paths correctly
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set environment variables for JSBSim to find the correct paths
        os.environ["JSBSIM_ROOT_DIR"] = os.path.join(script_dir, "jsbsim_xml")
        
        # --------------------------------------------
        # Set up Kafka
        # --------------------------------------------
        transport = middleware.get_transport("kafka")
        
        # Subscribe to camera images topic
        transport.subscribe_raw(
            "aerosim::types::CompressedImage", 
            "aerosim.renderer.responses", 
            on_camera_data
        )
        
        # Subscribe to flight data topic
        transport.subscribe(
            aerosim_types.PrimaryFlightDisplayData,
            "aerosim.actor1.primary_flight_display_data",
            on_flight_display_data,
        )

        # Use absolute path for config file
        config_file = os.path.join(script_dir, "config/sim_config_simulink_cosim_and_fmu.json")
        logger.info(f"Starting AeroSim simulation with config: {config_file}")
        
        aerosim = AeroSim()
        aerosim.run(config_file)

        logger.info(
            "AeroSim simulation is co-simulating with Simulink. Use the Simulink model to control the target altitude."
        )
        logger.info("Press Ctrl+C to stop the simulation.")

        while True:
            # Process any commands from aerosim-app
            if command_queue:
                command = command_queue.pop()
                logger.info(f"Received command from aerosim-app: {command}")
                
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    finally:
        # --------------------------------------------
        # Stop AeroSim simulation
        if 'aerosim' in locals():
            aerosim.stop()
            logger.info("Simulation stopped")

async def run_websocket_servers():
    """Run the WebSocket servers for communication with aerosim-app"""
    logger.info("Starting WebSocket servers for aerosim-app communication...")
    # Start all three WebSocket servers (command, image, data)
    websocket_tasks = await start_websocket_servers(
        command_port=DEFAULT_COMMAND_PORT,
        image_port=DEFAULT_IMAGE_PORT,
        data_port=DEFAULT_DATA_PORT,
    )
    # Wait for all servers to complete (they run indefinitely)
    await asyncio.gather(*websocket_tasks)

if __name__ == "__main__":
    try:
        # Start the simulation in a separate thread
        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()

        # Start the WebSocket server in the main asyncio event loop
        asyncio.run(run_websocket_servers())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()