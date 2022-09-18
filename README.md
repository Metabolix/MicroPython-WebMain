# WebMain for MicroPython

This is a main loop with a small web server, written in MicroPython (originally for Raspberry Pi Pico W). It provides remote administration (file manager), multiplexing (multiple projects on one device) and a simple interface for handling HTTP requests. It's not meant for time-critical applications, because a blocking HTTP request or activity in another module will inevitably cause delays.

## Features

- WLAN configuration as access point or client.
- PING client and WLAN automatic reconnection.
- NTP client to synchronize real-time clock.
- HTTP server with simple request handling.
- Module system for adding own web pages.
- Periodic callbacks to implement background tasks.
- File manager.

## Usage

- Copy all provided files (`.py` and `.html`) on your device.
- Create `wlan.conf`: `{"ssid": "MyNet", "key": "my-secrets", "ap": false}`.
- Run [Example.py](Example.py) and browse to `http://ip/WebMain`.
- Write your own projects as callable functions or classes.
- Write a main class to load your modules and start the server.

Expected result:

```
WLAN connecting, ssid MyNet
WLAN ready, IP 192.168.0.123, gateway 192.168.0.1
Starting HTTP server http://192.168.0.123/
NTP synced: 2022-09-18T23:45:30Z
```

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See [LICENSE](LICENSE) for more details.
