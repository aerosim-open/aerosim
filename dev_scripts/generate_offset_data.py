import argparse

from aerosim import AeroSim
from confluent_kafka import Producer, Consumer, KafkaException

import numpy as np
import json

import matplotlib.pyplot as plt
from scipy.interpolate import Rbf

import time
import uuid


# Function to send command and wait for response
def send_command_and_wait(command):
    producer.produce(topic_command, json.dumps(command).encode("utf-8"))
    producer.flush()
    print(f"Sent command: {command['uuid']}")

    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            print(msg.error())
            break

        response = json.loads(msg.value().decode("utf-8"))
        if response.get("uuid") == command["uuid"]:
            print(f"Received response: {response}")
            responses.append(response)
            break


def process_responses(responses):
    latitudes = np.array([resp["parameters"]["lat"] for resp in responses])
    longitudes = np.array([resp["parameters"]["lon"] for resp in responses])
    altitudes = np.array([resp["parameters"]["altitude_offset"] for resp in responses])
    return latitudes, longitudes, altitudes


def rbf_interpolation(
    latitudes, longitudes, altitudes, grid_spacing=0.001, padding_percentage=0.05
):
    if len(latitudes) == 1:
        lat_padding = grid_spacing * 5
        lon_padding = grid_spacing * 5
        lat_min = latitudes[0] - lat_padding
        lat_max = latitudes[0] + lat_padding
        lon_min = longitudes[0] - lon_padding
        lon_max = longitudes[0] + lon_padding

        lat_resolution = int((lat_max - lat_min) / grid_spacing) + 1
        lon_resolution = int((lon_max - lon_min) / grid_spacing) + 1

        lat_grid = np.linspace(lat_min, lat_max, lat_resolution)
        lon_grid = np.linspace(lon_min, lon_max, lon_resolution)
        lon_mesh, lat_mesh = np.meshgrid(lat_grid, lon_grid)

        z_mesh = np.full_like(lon_mesh, altitudes[0])

        return lat_mesh, lon_mesh, z_mesh

    lat_min, lat_max = min(latitudes), max(latitudes)
    lon_min, lon_max = min(longitudes), max(longitudes)

    lat_padding = (lat_max - lat_min) * padding_percentage
    lon_padding = (lon_max - lon_min) * padding_percentage
    padding = max(lat_padding, lon_padding)

    lat_min -= padding
    lat_max += padding
    lon_min -= padding
    lon_max += padding

    lat_resolution = int((lat_max - lat_min) / grid_spacing) + 1
    lon_resolution = int((lon_max - lon_min) / grid_spacing) + 1

    lat_grid = np.linspace(lat_min, lat_max, lat_resolution)
    lon_grid = np.linspace(lon_min, lon_max, lon_resolution)
    lat_mesh, lon_mesh = np.meshgrid(lat_grid, lon_grid)

    rbf_interpolator = Rbf(latitudes, longitudes, altitudes, function="multiquadric")
    z_mesh = rbf_interpolator(lat_mesh, lon_mesh)

    return lat_mesh, lon_mesh, z_mesh


def create_offset_map_json(lat_mesh, lon_mesh, z_mesh, filename):
    lat_min, lat_max = lat_mesh.min(), lat_mesh.max()
    lon_min, lon_max = lon_mesh.min(), lon_mesh.max()

    lat_resolution = lat_mesh.shape[1]
    lon_resolution = lon_mesh.shape[0]

    print(z_mesh)

    offset_map_data = {
        "bounds": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
        },
        "lat_resolution": lat_resolution,
        "lon_resolution": lon_resolution,
        "offsets": z_mesh.flatten().tolist(),
    }

    with open(filename, "w") as f:
        json.dump(offset_map_data, f, indent=4)
    print(f"Offset map saved to {filename}")


def plot_interpolated_grid(
    lat_mesh, lon_mesh, z_mesh, latitudes, longitudes, altitudes
):
    # Calculate the aspect ratio based on the lat/lon ranges
    lat_range = lat_mesh.max() - lat_mesh.min()
    lon_range = lon_mesh.max() - lon_mesh.min()
    aspect_ratio = lat_range / lon_range

    # Set the figure size based on the aspect ratio
    plt.figure(figsize=(10 * aspect_ratio, 10))

    # Plot the interpolated grid with a color map
    contour = plt.contourf(lat_mesh, lon_mesh, z_mesh, cmap="viridis", levels=100)
    plt.colorbar(contour, label="Altitude")

    # Plot original data points with altitude values
    plt.scatter(latitudes, longitudes, c="red", s=20, edgecolor="black", zorder=5)
    for lat, lon, alt in zip(latitudes, longitudes, altitudes):
        plt.text(
            lat, lon, f"{alt:.2f}", color="white", fontsize=8, ha="center", va="center"
        )

    # Plot formatting
    plt.title("RBF Interpolated Grid")
    plt.xlabel("Latitude")
    plt.ylabel("Longitude")
    plt.gca().set_aspect("equal", adjustable="box")  # Keep the proportions accurate
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offset map json file generation")
    parser.add_argument("--input", required=True, help="Path to the input JSON file")
    parser.add_argument(
        "--output",
        help="Path to the output JSON file (optional, default: 'offset_map.json')",
    )
    parser.add_argument(
        "--grid_spacing",
        type=float,
        default=0.01,
        help="Grid spacing in degrees (default: 0.01)",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.05,
        help="Percentage padding around the grid (default: 0.05)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Enable visualization of the interpolated grid",
    )

    args = parser.parse_args()

    commands = []
    responses = []

    # Load commands from input JSON file
    with open(args.input, "r") as f:
        input_data = json.load(f)
        for command in input_data:
            commands.append(
                {
                    "uuid": str(uuid.uuid4()),
                    "command_type": "measure_altitude_offset",
                    "parameters": command,
                }
            )

    # --------------------------------------------
    # Run AeroSim simulation
    aerosim = AeroSim()
    aerosim.run("config/generate_offset_data_config.json")

    # --------------------------------------------
    # Configuration
    server_addr = "127.0.0.1:9092"
    topic_command = "aerosim.renderer.commands"
    topic_response = "aerosim.renderer.responses"

    # Create Producer
    producer = Producer({"bootstrap.servers": server_addr})

    # Create Consumer
    consumer = Consumer(
        {
            "bootstrap.servers": server_addr,
            "group.id": "altitude_offset_test_group",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([topic_response])

    # Sleep for 5 seconds to allow the simulation to start
    time.sleep(2)

    # Send commands sequentially
    try:
        for command in commands:
            send_command_and_wait(command)
    except KeyboardInterrupt:
        pass

    consumer.close()
    aerosim.stop()

    latitudes, longitudes, altitudes = process_responses(responses)
    print(f"Latitudes: {latitudes}")
    print(f"Longitudes: {longitudes}")
    print(f"Altitudes: {altitudes}")

    # Perform RBF interpolation with specified grid spacing and padding
    lat_mesh, lon_mesh, z_mesh = rbf_interpolation(
        latitudes, longitudes, altitudes, args.grid_spacing, args.padding
    )

    # Save the interpolated data to the specified output file
    output_file = args.output if args.output else "offset_map.json"
    create_offset_map_json(lat_mesh, lon_mesh, z_mesh, output_file)

    # Visualize the interpolated grid if --visualize is set
    if args.visualize:
        plot_interpolated_grid(
            lat_mesh, lon_mesh, z_mesh, latitudes, longitudes, altitudes
        )
