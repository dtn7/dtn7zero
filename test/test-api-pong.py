import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


setup("dtn://node2/")

start_background_update_thread(sleep_time_milliseconds=100)


def pong_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
    print("sending back pong {}".format(payload))
    pong.send(payload, full_source_uri)


pong = register("pong", pong_callback)


try:
    while True:
        time.sleep(2)
except KeyboardInterrupt:
    pass

