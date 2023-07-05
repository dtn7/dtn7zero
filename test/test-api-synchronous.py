from dtn7zero import setup, register, run_forever
from py_dtn7.bundle import PrimaryBlock


setup("dtn://node1/")


def ping_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
    print("received pong: {}".format(payload))


ping = register("ping", ping_callback)


def pong_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
    print("sending back pong {}".format(payload))
    pong.send(payload, full_source_uri)


pong = register("pong", pong_callback)


counter = 1


def main_loop():
    global counter
    payload = str(counter).encode()
    print("sending ping: {}".format(payload))
    ping.send(payload, "dtn://node1/pong")
    counter += 1


run_forever(main_loop, loop_callback_interval_milliseconds=2000, sleep_time_milliseconds=100)
