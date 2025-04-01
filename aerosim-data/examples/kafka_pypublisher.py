import time

from aerosim_data import middleware
from aerosim_data import types

def main():
    transport = middleware.get_transport("kafka")
    while True:
        transport.publish("vector3", types.Vector3(1, 1, 1))
        transport.publish("json", {"posx": 99.0, "posy": 99.9})
        time.sleep(1)

if __name__ == '__main__':
    main()
