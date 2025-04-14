import sys, logging
import asyncio, json
import time

import xviz_avs
from xviz_avs.server import XVIZServer, XVIZBaseSession

from aerosim_data import types as aerosim_types
from aerosim_data import middleware

"""
This example shows how to retrieve data from the Aerosim through a xviz server
"""


class SampleServer:
    def __init__(self, live=True, duration=10):
        self._timestamp = time.time()
        self._duration = duration
        self._live = live
        self._metadata = None

        # Set up middleware transport and subscribe to vehicle state
        self.transport = middleware.get_transport("kafka")
        self.transport.subscribe(
            aerosim_types.JsonData,
            "aerosim.actor1.vehicle_state",
            self.on_vehicle_state_data,
        )

        self.cur_speed = 0.0
        self.cur_altitude = 0.0

    def get_metadata(self):
        if not self._metadata:

            builder = xviz_avs.XVIZMetadataBuilder()

            builder.stream("/actor/altitude").category(
                xviz_avs.CATEGORY.TIME_SERIES
            ).type(xviz_avs.SCALAR_TYPE.FLOAT).unit("m")
            builder.stream("/actor/speed").category(xviz_avs.CATEGORY.TIME_SERIES).type(
                xviz_avs.SCALAR_TYPE.FLOAT
            ).unit("km/h")

            if not self._live:
                log_start_time = self._timestamp
                builder.start_time(log_start_time).end_time(
                    log_start_time + self._duration
                )
            self._metadata = builder.get_message()

        if self._live:
            return {"type": "xviz/metadata", "data": self._metadata.to_object()}
        else:
            return self._metadata

    def get_message(self, time_offset):
        timestamp = self._timestamp + time_offset

        builder = xviz_avs.XVIZBuilder(metadata=self._metadata)
        builder.timestamp(timestamp)

        builder.time_series("/actor/altitude").timestamp(timestamp).value(
            self.cur_altitude
        )
        builder.time_series("/actor/speed").timestamp(timestamp).value(self.cur_speed)

        data = builder.get_message()

        if self._live:
            return {"type": "xviz/state_update", "data": data.to_object()}
        else:
            return data

    def on_vehicle_state_data(self, data, _):

        self.cur_altitude = -data["state"]["pose"]["position"]["z"]
        self.cur_speed = data["velocity"]["x"] * 3.6  # convert to km/h


class ServerSession(XVIZBaseSession):
    def __init__(self, socket, request, server=SampleServer()):
        super().__init__(socket, request)
        self._server = server
        self._socket = socket

    def on_connect(self):
        print("Connected!")

    def on_disconnect(self):
        print("Disconnected!")

    async def main(self):
        metadata = self._server.get_metadata()
        await self._socket.send(json.dumps(metadata))

        t = 0
        while True:
            message = self._server.get_message(t)
            await self._socket.send(json.dumps(message))

            t += 0.05
            await asyncio.sleep(0.05)


class ServerHandler:
    def __init__(self):
        pass

    def __call__(self, socket, request):
        return ServerSession(socket, request)


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logging.getLogger("xviz-server").addHandler(handler)

    xviz_server = XVIZServer(ServerHandler(), port=8081)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(xviz_server.serve())
    loop.run_forever()
