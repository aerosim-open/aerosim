import time

from aerosim_data import middleware
from aerosim_data import types

def main():
    transport = middleware.get_transport("dds")
    while True:
        transport.publish("vector3", types.Vector3(1.0, 1.0, 1.0))
        transport.publish("json", {"posx": 99.0, "posy": 99.9})
        time.sleep(1)

if __name__ == '__main__':
    main()
