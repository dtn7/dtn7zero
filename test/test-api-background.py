import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


setup("dtn://node1/")

start_background_update_thread(_sleep_time_seconds=0.1)


def ping_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
    print("received pong: {}".format(payload))


ping = register("ping", ping_callback)


def pong_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
    print("sending back pong {}".format(payload))
    pong.send(payload, full_source_uri)


pong = register("pong", pong_callback)


counter = 1
try:
    while True:
        time.sleep(2)
        payload = str(counter).encode()
        print("sending ping: {}".format(payload))
        ping.send(payload, "dtn://node1/pong")
        counter += 1
except KeyboardInterrupt:
    pass

