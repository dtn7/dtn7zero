"""
This example shows how to send a ping and react to the response via polling

It should be used in combination with any echo example (remote_echo_callback.py, remote_echo_poll.py) on another machine.
Both machines must be running in the same local network.
"""
from dtn7zero import setup, register, start_background_update_thread
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout


setup("dtn://node-a/")

start_background_update_thread()

ping = register("ping")


last_ping_sent = 0
counter = 1
try:
    while True:
        payload, full_source_uri, full_destination_uri, primary_block = ping.poll()
        if payload is not None:
            print("received echo {}".format(payload))

        if is_timestamp_older_than_timeout(last_ping_sent, 1000):
            print("sending ping {}".format(counter))
            ping.send(str(counter).encode(), "dtn://node-b/echo")
            counter += 1
            last_ping_sent = get_current_clock_millis()
except KeyboardInterrupt:
    pass
