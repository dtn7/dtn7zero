# dtn7zero
This is a DTN7 [RFC9171](https://datatracker.ietf.org/doc/html/rfc9171) compliant python implementation (work-in-progress) with a [NetworkZero](https://networkzero.readthedocs.io/en/latest/networkzero.html) like API.

The current features are:
- a full bundle protocol agent (without fragment, CRC, and status-report generation support -> todo)
- a minimal TCP convergence layer
- a [dtn7-rs](https://github.com/dtn7/dtn7-rs) convergence layer, using the [HTTP/REST](https://github.com/dtn7/dtn7-rs/blob/master/doc/http-client-api.md) interface
- automatic local-network node-discovery via IPND module
- a standalone 'external' endpoint (which connects to a [dtn7-rs](https://github.com/dtn7/dtn7-rs) via the [HTTP/REST](https://github.com/dtn7/dtn7-rs/blob/master/doc/http-client-api.md)) interface
- a simplified [NetworkZero](https://networkzero.readthedocs.io/en/latest/networkzero.html) like API to easily get started
- full MicroPython support (tested on an ESP32-GENERIC)
- experimental ESPNOW cla (details can be found in the source code: *dtn7zero/convergence_layer_adapters/espnow_cla.py*)
- (currently uses epidemic routing and in-memory storage managing)
- (with extendability for new convergence layer adapters, routing algorithms, and storage managers)

## Getting Started

To use dtn7zero in your CPython environment, simply install it via pip (or pip3 on linux):
```shell
$ pip install --upgrade dtn7zero
```
The most simple example on what you can do:
```python
import time

from dtn7zero import setup, start_background_update_thread

node_endpoint = setup("dtn://node1/", print)

start_background_update_thread()

node_endpoint.send(b'hello world', "dtn://node1/")

time.sleep(1)
```
Further examples for the 'simple' API can be found under `./examples` in the GitHub repository.

For a deeper dive into the underlying concepts and the full-fledged dtn implementation, take a look at the 
`dtn7zero.api` module implementation and the tests under `./test`.

## MicroPython Installation Guide
Installation has been successfully tested on Windows and Linux (x86_64 and arm64). The required
[mpy-cross](https://pypi.org/project/mpy-cross/) has been shown to have installation issues on Mac M1s
under Mac OS X and may have to be built and installed manually.

This whole project was tested on an ESP32 (GENERIC) and this installation guide is tailored for the ESP32.
If you plan to use another microcontroller you might need to do adjustments 
(most certainly the MicroPython installation, and the MPY_MARCH in esp-deployment.py).

Important note for linux: it may be that mpremote assumes another USB device with higher priority than the ESP32.
In that case all mpremote commands (especially inside esp-deployment.py) will fail as no communication is possible.
Check all USB devices mpremote considers in priority order with `mpremote devs`.

### First Time MicroPython Installation For ESP32 (GENERIC)
1. download the newest [firmware](https://micropython.org/download/esp32/)
2. install the esp flash tool: `pip install esptool`
3. connect your ESP32 via USB and start a terminal at the location of the downloaded firmware
4. start the following command (with the correct USB port): \
`esptool --chip esp32 --port /dev/ttyUSB0 erase_flash` (you may have to invoke esptool with `esptool.py --chip ...` here and subsequently, you may also have hold **boot** to enter the bootloader on the ESP32)
5. start the following command (with the correct USB port and firmware name): \
`esptool --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-20220618-v1.19.1.bin` (you may have hold **boot** again to enter the bootloader on the ESP32)
6. done, you may now connect to it via: `mpremote` (installation via pip: `pip install mpremote`)

### Update To New MicroPython Version
1. download the newest [firmware](https://micropython.org/download/esp32/)
2. start the following command (with the correct USB port and firmware name): \
`esptool --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-20220618-v1.19.1.bin` (you may have hold **boot** to enter the bootloader on the ESP32)
3. done

### First Time dtn7zero Deployment
1. make sure you check out the repository and the submodules (especially py-dtn7)
2. install the mpremote tool: `pip install mpremote`
3. install the mpy-cross compiler tool: `pip install mpy-cross` (this may not work on Mac M1s under Mac OS X) 
4. populate wlan.json with an appropriate hostname and at least one ssid -> password mapping
5. check your connection to the ESP32 with: `mpremote`
6. copy wlan.json to your ESP32: `mpremote fs cp wlan.json :wlan.json`
7. copy boot.py to your ESP32: `mpremote fs cp boot.py :boot.py`
8. deploy the dtn7zero and dependencies onto the ESP32 (this can take a while): `python scripts/esp-deployment.py`
9. install required packages: `mpremote mip install urequests` and `mpremote mip install datetime`
10. done

### Continuous dtn7zero Deployment
1. check your connection to the ESP32 with: `mpremote`
2. deploy the changes of dtn7zero and dependencies onto the ESP32 (this can take a while): `python scripts/esp-deployment.py`
3. done

### First dtn7zero Functionality Check On MicroPython
1. you may check that wlan is connecting correctly (connect via `mpremote` and press **enable** for a soft reset)
2. you may also check that you can import dtn7zero (connect via `mpremote` and `import dtn7zero`)
3. you can also check that everything works (run the test script `mpremote run examples/local_ping_echo.py`)

### Additional MicroPython Tips & Tricks
The mpremote tool is normally interrupted by using `ctrl+c`. A special case is the REPL (simply call `mpremote`), which
can be exited by using `ctrl+~` (tested on Windows) or `ctrl+]` (Linux).

If you start a script on MicroPython (`mpremote run ...`) and disconnect the console (`mpremote` -> `ctrl+c`) then the script 
keeps running.

If you must access the REPL via mpremote, but a script is blocking, then call `mpremote` and press EN (enable) on the 
ESP32 for a soft-reset. Press `ctrl+c` a few times to interrupt the `boot.py` or `main.py` script execution. The session
state is stored, so any subsequent `mpremote` call will start at REPL as long as no power disconnect is performed.

You can deploy a script as `main.py` on MicroPython to be run every time the microcontroller gets power. \
You can also remove the script. MicroPython will only execute the script if it is present.
```shell
$ mpremote fs cp examples/remote_echo_callback.py :main.py
$ mpremote fs rm :main.py
```

Regarding `boot.py`: it is used for user-specific setup code and this framework uses a generic boot script that adjusts
the ESP32's frequency and connects to a Wi-Fi network (blocking until success). MicroPython will create a dummy `boot.py`
if none is present. MicroPython will not create a dummy `main.py` if none is present. MicroPython will first execute
the `boot.py` and then the `main.py` if it is present.


## Development Information

### Development Mode
You can install this project locally to directly reflect code changes in your environment.
Simply run this in the project root folder (requires at least pip v21.1):
```shell
$ python -m pip install --editable .
```

### Build
To build this project yourself you need the python [build](https://pypi.org/project/build/) tool, as well as [setuptools](https://pypi.org/project/setuptools/):
```shell
$ pip install --upgrade setuptools
$ pip install --upgrade build
```
Then you can simply run this command to build the project:
```shell
$ python -m build
```

### Publish
To publish this project you will probably update the version in `pyproject.toml`, [build](#build) the project, and then use [twine](https://pypi.org/project/twine/) to upload the build:
```shell
$ pip install --upgrade twine
```
```shell
$ python -m twine upload dist/*
```


## Useful Links
the DTN7 website: https://dtn7.github.io \
dtn7 go implementation: https://github.com/dtn7/dtn7-go \
dtn7 rust implementation: https://github.com/dtn7/dtn7-rs \
dtn7 python bundle implementation and dtn7rs-rest-api access: https://github.com/teschmitt/py-dtn7

Bundle Protocol 7 RFC: https://datatracker.ietf.org/doc/html/rfc9171 \
Bundle Protocol Security (BPSec) RFC: https://datatracker.ietf.org/doc/html/rfc9172 \
Default Security Contexts for BPSec RFC: https://datatracker.ietf.org/doc/html/rfc9173 \
TCP Convergence-Layer Protocol Version 4 RFC: https://datatracker.ietf.org/doc/html/rfc9174 \
Minimal TCP Convergence-Layer Protocol RFC (draft): https://datatracker.ietf.org/doc/html/draft-ietf-dtn-mtcpcl-01 \
UDP Convergence Layer RFC (draft): https://datatracker.ietf.org/doc/html/draft-sipos-dtn-udpcl-01

Outdated Standards: \
DTN URI Scheme: https://www.ietf.org/archive/id/draft-irtf-dtnrg-dtn-uri-scheme-00.html

## Further Research
This is some information gathered about future mesh extensions:

1. [ESP-Mesh(ESP-WIFI-Mesh)](https://www.espressif.com/en/products/sdks/esp-wifi-mesh/overview)
   - a special mesh standard which is based of Wi-Fi and uses the special AP_STA mode 
   - no micropython implementation known

2. [ESP-NOW](https://www.espressif.com/en/products/software/esp-now/overview)
   - a special p2p mode, which is based of Wi-Fi and can send data to neighbouring devices via MAC addressing
   - no mesh protocol, but broadcast is possible, looks promising to build an esp32-dtn-mesh
   - non-official, but tested micropython [library](https://github.com/glenn20/micropython/blob/espnow-g20/docs/library/espnow.rst) available, as well as [builds](https://github.com/glenn20/micropython-espnow-images) with the current firmware

3. Alternative: AP_STA mode for simultaneous AP and STA without explicit ESP-MESH usage
   - only available for [Arduino+C](https://techtutorialsx.com/2021/01/04/esp32-soft-ap-and-station-modes/)
   - [painlessMesh](https://gitlab.com/painlessMesh/painlessMesh) also uses this mode to build its mesh

### Open End Topics / Known Issues
- fragment, CRC, status-report generation support
- dtn7rs-rest-cla and in-memory storage together use too much RAM for MicroPython (therefore the dtn7rs-rest-cla is disabled in the simple API)
- public documentation (currently all information must be gathered from doc-strings and examples)
