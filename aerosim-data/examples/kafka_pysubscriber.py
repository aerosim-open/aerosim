import time

from aerosim_data import middleware
from aerosim_data import types

class Watcher(object):
    def __init__(self, transport):
        self.transport = transport
        self.serializer = transport.get_serializer()

        self.counter_vector = 0
        self.counter_json = 0
        self.counter_raw = 0
        self.counter_raw_json = 0

        self.transport.subscribe(types.Vector3, "vector3", self.log_vector)
        self.transport.subscribe(types.JsonData, "json", self.log_json)

        # Raw subscribers
        self.transport.subscribe_all_raw(
            [("aerosim::types::Vector3", "vector3"),
             ("aeorsim::types::JsonData", "json")],
            self.log_raw
        )

        self.transport.subscribe_raw("aerosim::types::Vector3", "vector3", self.log_raw_json)

    def log_vector(self, vector, metadata):
        self.counter_vector += 1
        print(f"#{self.counter_vector} Recevied new vector [{metadata.topic}]-> x: {vector.x}, y: {vector.y}, z: {vector.z}")

    def log_json(self, json, metadata):
        self.counter_json += 1
        x = json["posx"]
        y = json["posy"]
        print(f"#{self.counter_json} Received new json position [{metadata.topic}]-> {x}, {y}")

    def log_raw(self, payload):
        self.counter_raw += 1
        metadata = self.serializer.deserialize_metadata(payload)

        if metadata.type_name == "aerosim::types::JsonData":
            data = self.serializer.deserialize_data(types.JsonData, payload).to_dict()
        elif metadata.type_name == "aerosim::types::Vector3":
            data = self.serializer.deserialize_data(types.Vector3, payload).to_dict()

        print(f"#{self.counter_raw} Recevied raw [({metadata.topic}, {metadata.type_name})]-> data: {data}")

    def log_raw_json(self, payload):
        self.counter_raw_json += 1
        metadata = self.serializer.deserialize_metadata(payload)

        # Deserialize payload to JSON
        data = self.serializer.to_json(metadata.type_name, payload)

        print(f"#{self.counter_raw_json} Recevied raw (json) [({metadata.topic}, {metadata.type_name})]-> json: {data}")


def main():
    transport = middleware.get_transport("kafka")
    watcher = Watcher(transport)
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
