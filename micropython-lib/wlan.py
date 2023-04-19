import json
import time
import network


try:
    with open('wlan.json') as f:
        wlan_config = json.load(f)
    hostname = wlan_config['HOSTNAME']
    wlan_credentials = wlan_config['WLAN_CREDENTIALS']
    assert len(wlan_credentials) > 0
except OSError:
    raise Exception('wlan config does not exist, but is mandatory')
except ValueError:
    raise Exception('wlan config is no valid json')
except KeyError:
    raise Exception('wlan config must contain a HOSTNAME and non empty WLAN_CREDENTIALS')
except AssertionError:
    raise Exception('WLAN_CREDENTIALS may not be empty')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
time.sleep_us(100)  # bug in micropython 19.1, hostname may not be set directly after wlan activation
wlan.config(dhcp_hostname=hostname)

latest_connected_network = None


def connect():
    global latest_connected_network

    if not wlan.active():
        wlan.active(True)

    while not wlan.isconnected():
        wlan_list = wlan.scan()

        if not wlan_list:
            # empty list on active wlan bug -> must restart wlan interface
            wlan.active(False)
            wlan.active(True)
            continue

        last_ssid = None
        for ssid, _, _, _, _, _ in wlan_list:
            ssid = ssid.decode()

            if ssid in wlan_credentials:
                last_ssid = ssid

                wlan.connect(ssid, wlan_credentials[ssid])

                start_time = time.ticks_ms()
                while (not wlan.isconnected()) and (time.ticks_diff(time.ticks_ms(), start_time) < 5000):
                    time.sleep_ms(200)

                if wlan.isconnected():
                    print('some buffer for {} bug'.format('print'))
                    print('connected to wlan: {} as {}'.format(ssid, hostname))
                    latest_connected_network = ssid
                    break

        if not wlan.isconnected():
            print('no connectable network found. retrying...')
            time.sleep_ms(200)

            # sometimes it does connect for some reason
            if wlan.isconnected():
                latest_connected_network = last_ssid


def reconnect():
    attempts = 0

    while not wlan.isconnected():
        try:
            print('reconnecting wifi...')
            if wlan.isconnected():
                return

            if latest_connected_network is None:
                raise Exception('reconnect is called before connect')

            wlan.active(True)

            ssid = latest_connected_network
            wlan.connect(ssid, wlan_credentials[ssid])

            start_time = time.ticks_ms()
            while (not wlan.isconnected()) and (time.ticks_diff(time.ticks_ms(), start_time) < 5000):
                pass
        except OSError:
            if attempts >= 2:
                raise

            wlan.active(False)
            wlan.active(True)
            attempts += 1

    print('done')


def isconnected():
    return wlan.isconnected()


def ifconfig():
    return wlan.ifconfig()
