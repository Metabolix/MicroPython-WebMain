import network, os, machine
from Timeout import Timeout

class SimpleWLAN:
    """Connect to WLAN: x = SimpleWLAN("ssid", "key", ap = False)"""

    def __init__(self, ssid = None, key = None, ap = False):
        self.ap, self.ssid, self.key = ap, ssid, key
        if ap and not ssid:
            self.ssid = (os.uname()[0] + "-" + "".join("%02x" % i for i in machine.unique_id()))[:32]
        self.wlan = None
        self.connect()

    def disconnect(self):
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
            return True
        if not 0 <= s <= 3 and s != self._failed:
            self._failed = s
            print(f"WLAN failed ({s})")
        self._connect_timeout.expired() and self.connect()
        return False
