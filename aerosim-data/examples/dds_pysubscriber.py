import time

from aerosim_data import middleware
from aerosim_data import types

class Watcher(object):
    def __init__(self, transport):
        self.transport = transport

        self.counter_vector = 0
        self.counter_json = 0

        self.transport.subscribe(types.Vector3, "vector3", self.log_vector)
        self.transport.subscribe(types.JsonData, "json", self.log_json)

    def log_vector(self, vector, metadata):
        self.counter_vector += 1
        print(f"#{self.counter_vector} Recevied new vector [{metadata.topic}]-> x: {vector.x}, y: {vector.y}, z: {vector.z}")

    def log_json(self, json, metadata):
        self.counter_json += 1
        x = json["posx"]
        y = json["posy"]
        print(f"#{self.counter_json} Received new json position [{metadata.topic}]-> {x}, {y}")

def main():
    transport = middleware.get_transport("dds")
    watcher = Watcher(transport)
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
