# AeroSim

AeroSim is a comprehensive flight simulation framework that combines Rust and Python components to provide a powerful and flexible simulation environment.

## Features

- **Core Simulation**: Run flight simulations with FMU models and orchestration
- **WebSockets Integration**: Communicate with aerosim-app for visualization and control
- **Input Handling**: Process input from keyboard, gamepad, and remote sources
- **Visualization**: Stream camera images and flight display data
- **Cross-Platform**: Works on both Windows and Linux

## Installation

```bash
# Using pip
pip install aerosim

# Using uv
uv add aerosim
```

## Quick Start

```python
import asyncio
from aerosim import AeroSim, start_websocket_servers

# Create and run a simulation
sim = AeroSim(enable_websockets=True)
sim.run("config/sim_config.json")

# Start WebSockets servers for aerosim-app communication
asyncio.run(start_websocket_servers())
```

## Usage with aerosim-app

1. Install and launch AeroSim:
   ```bash
   # Windows
   launch_aerosim.bat --unreal --pixel-streaming

   # Linux
   ./launch_aerosim.sh --unreal --pixel-streaming
   ```

2. Start the aerosim-app:
   ```bash
   cd ../aerosim-app
   bun run dev
   ```

3. Run one of the example scripts:
   ```bash
   python examples/simple_flight_with_app.py
   ```

## Package Structure

- `aerosim.core`: Core simulation classes
- `aerosim.io`: Input/output handling
  - `aerosim.io.websockets`: WebSockets integration
  - `aerosim.io.input`: Input handling
- `aerosim.visualization`: Visualization utilities
- `aerosim.utils`: Common utility functions

## Examples

The package includes several example scripts:

- `first_flight.py`: First flight program to get started
- `pilot_control_with_flight_deck.py`: Pilot control with flight deck
- `autopilot_daa_scenario.py`: Autopilot with detect and avoid scenario
- `simulink_cosim_and_fmu.py`: Simulink co-simulation with FMU models

## Dependencies

The package depends on:

- `aerosim_world`: Core simulation engine
- `aerosim_data`: Data types and middleware
- `aerosim_core`: Core utilities
- `websockets`: WebSockets communication
- `pygame`: Input handling
- `opencv-python`: Image processing
- `numpy`: Numerical operations