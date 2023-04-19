"""
This example shows how to react to incoming messages via polling.

It should be used in combination with any ping example (remote_ping_callback.py, remote_ping_poll.py) on another machine.
Both machines must be running in the same local network.
"""
from dtn7zero import setup, register, start_background_update_thread

setup("dtn://node-b/")

echo = register("echo")

start_background_update_thread()


try:
    while True:
        payload, full_source_uri, full_destination_uri, primary_block = echo.poll()
        if payload is not None:
            print("received ping {}, sending back echo".format(payload))
            echo.send(payload, full_source_uri)
except KeyboardInterrupt:
    pass
