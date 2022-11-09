import network, os, machine
from Timeout import Timeout
from SimplePing import SimplePing

class SimpleWLAN:
    """Connect to WLAN: x = SimpleWLAN("ssid", "key", ap = False)"""

    def __init__(self, ssid = None, key = None, ap = False, keepalive_ping = True):
        self.ap, self.ssid, self.key = ap, ssid, key
        if ap and not ssid:
            self.ssid = (os.uname()[0] + "-" + "".join("%02x" % i for i in machine.unique_id()))[:32]
        self.wlan = None
        self._keepalive_ping = keepalive_ping
        self._ping = None
        self._ping_broken = 0
        self.connect()

    @classmethod
    def from_config(self, filename = "wlan.conf", fallback = True):
        try:
            conf = {"ssid": None, "key": None, "ap": False, "keepalive_ping": True}
            import json
            with open(filename, "r") as f:
                for k, v in json.load(f).items():
                    if k in conf:
                        conf[k] = v
        except:
            print(f"Failed to load config from {filename}. Example contents:")
            print('{"ssid": "MyNet", "key": "my-secrets", "ap": false}')
            if not fallback:
                return
            conf["ap"] = True
        return self(**conf)

    def disconnect(self):
        if self._ping:
            self._ping.close()
            self._ping = None
        if self.wlan:
            self.wlan.disconnect()
            self.wlan.active(False)
            self.wlan = None

    def connect(self):
        self.disconnect()
        self.ip = self.gateway = None
        self._failed = 0
        self._connect_timeout = Timeout(60_000)
        if self.ap:
            print(f"WLAN AP, ssid {self.ssid}")
            self.wlan = network.WLAN(network.AP_IF)
            if self.key:
                self.wlan.config(ssid = self.ssid, security = 4, key = self.key)
            else:
                self.wlan.config(ssid = self.ssid)
            self.wlan.active(True)
        else:
            print(f"WLAN connecting, ssid {self.ssid}")
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.key)

    def connected(self):
        s = self.wlan.status()
        if s == 3:
            if not self.ip:
                x = self.wlan.ifconfig()
                self.ip, self.gateway = x[0], x[2]
                print(f"WLAN ready, IP {self.ip}, gateway {self.gateway}")
            if self._keepalive_ping:
                return self._ping_or_reconnect()
            return True
        if not 0 <= s <= 3 and s != self._failed:
            self._failed = s
            print(f"WLAN failed ({s})")
        self._connect_timeout.expired() and self.connect()
        return False

    def _ping_or_reconnect(self):
        if self._ping and self._ping.done() and self._ping.ms():
            self._ping = None
            self._ping_broken = 0
        if not self._ping:
            self._ping = SimplePing(self.gateway, count = 7, interval = 10_000, timeout = 10_000)
            return True
        if not self._ping.done():
            return True
        if self._ping.broken:
            self._ping_broken += 1
        print(f"PING failed, reconnecting.")
        self.connect()
        return False

    def is_broken(self, limit = 5):
        return self._ping_broken >= limit
