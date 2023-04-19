"""
This is the MicroPython boot.py for this projects ESP32 chips.
This script gets executed on every startup before main.py.

We will activate WiFi station-connection, but not WebREPl (web cli) as it is not reliable
"""

import machine
# import webrepl
# import os

try:
    from wlan import connect, ifconfig
    connect()
    print('network config: {}\n'.format(ifconfig()))
except KeyboardInterrupt:
    print('interrupt by user...moving on without wlan\n')
except ImportError:
    print('lh_lib does not exist...moving on without wlan\n')


# os.dupterm(None, 1)  # disable REPL on UART(0)

machine.freq(240000000)  # ESP32 maximum frequency
print('adjusted machine frequency to max: 240MHz (default: 160MHz)\n\n')

# machine.freq(160000000)  # ESP8266 maximum frequency
# print('adjusted machine frequency to max: 160MHz (default: 80MHz)\n\n')

# WEBREPL_PASSWORD = 'esp32batch'
# webrepl.start(password=WEBREPL_PASSWORD)
# print("webREPL started with password: {}".format(WEBREPL_PASSWORD))
