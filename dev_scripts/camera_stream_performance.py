from aerosim_data import types as aerosim_types
from aerosim_data import middleware

import collections
import time
import statistics

"""
This script measures image metrics such as rate, latency, and compression.  
By default, it processes 1000 images, but you can stop it anytime with Ctrl+C.  
The metrics will still be calculated based on the images processed before stopping.
"""

serializer = middleware.BincodeSerializer()

TOTAL_IMAGES = 1000

# Images received per second (starting from the first received image).
timestamps = collections.defaultdict(int)

latencies = []
compression = []

start_timestamp = 0
images_received = 0


def on_sensor_data(payload):
    global start_timestamp, images_received

    if images_received >= TOTAL_IMAGES:
        return

    metadata, data = serializer.deserialize_message(
        aerosim_types.CompressedImage, payload
    )

    # Save some useful data to compute statistics later
    timestamp_generated = metadata.timestamp_platform.to_millis()
    timestamp_received = aerosim_types.TimeStamp.now().to_millis()
    latency = timestamp_received - timestamp_generated

    if images_received == 0:
        start_timestamp = timestamp_received

    timestamps[int((timestamp_received - start_timestamp) / 1000.0)] += 1
    latencies.append(latency)
    compression.append((4 * 1920 * 1080) / len(data.data))

    images_received += 1


def report_statistics():

    # Discard images from the last second, as they may be incomplete.
    _ = timestamps.pop(max(timestamps))

    if len(timestamps) > 1:
        rates = list(timestamps.values())

        print("\nRate Statistics:")
        print(f"  -> Mean: {statistics.mean(rates):.2f} images/s")
        print(f"  -> Variance: {statistics.variance(rates):.2f}")
        print(f"  -> Minimum: {min(rates):.2f} images/s")
        print(f"  -> Maximum: {max(rates):.2f} images/s")

    if len(latencies) > 1:
        print("\nLatency Statistics:")
        print(f"  -> Mean: {statistics.mean(latencies):.2f} ms")
        print(f"  -> Variance: {statistics.variance(latencies):.2f}")
        print(f"  -> Minimum: {min(latencies):.2f} ms")
        print(f"  -> Maximum: {max(latencies):.2f} ms")

    if len(compression) > 1:
        print(f"\nCompression: {statistics.mean(compression):.2f}")


# Middleware transport
transport = middleware.get_transport("kafka")
transport.subscribe_raw(
    "aerosim::types::CompressedImage", "aerosim.renderer.responses", on_sensor_data
)

try:
    while images_received < TOTAL_IMAGES:
        print(f"\rProcessed: {images_received}/{TOTAL_IMAGES}", end="")
        time.sleep(1)
    print(f"\rProcessed: {images_received}/{TOTAL_IMAGES}", end="")
    report_statistics()
except KeyboardInterrupt:
    report_statistics()
