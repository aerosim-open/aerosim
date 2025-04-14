from aerosim_data import types as aerosim_types
from aerosim_data import middleware

import cv2
import numpy as np
from collections import deque

image_queue = deque(maxlen=1)
serializer = middleware.BincodeSerializer()

cv2.namedWindow("Camera Preview")


def on_sensor_data(payload):

    _, data = serializer.deserialize_message(aerosim_types.CompressedImage, payload)

    # Convert bytes to NumPy array
    image_array = np.frombuffer(data.data, dtype=np.uint8)

    image_queue.append(cv2.imdecode(image_array, cv2.IMREAD_COLOR))


# Set up middleware transport and subscribe to vehicle state
transport = middleware.get_transport("kafka")
transport.subscribe_raw(
    "aerosim::types::CompressedImage", "aerosim.renderer.responses", on_sensor_data
)

while True:
    if image_queue:

        image_rgb = image_queue.pop()
        cv2.imshow("Camera Preview", image_rgb)

    # Exit when pressing ESC
    key = cv2.waitKey(20)
    if key == 27:
        break
