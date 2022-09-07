"""Very simplified NTP implementation."""

import socket, struct, time, machine
from Timeout import Timeout

class SimpleNTPClient:
    """Query NTP

    Synchronous query and RTC sync:
    time_tuple = SimpleNTPClient().wait()
    machine.RTC().datetime(time_tuple)

    Asynchronous query; precision depends on poll interval!
    ntp = SimpleNTPClient(server, timeout)
    while not ntp.done():
        do_other_stuff()
    time_tuple = ntp.datetime()
    """

    def __init__(self, server = "pool.ntp.org", timeout = 5_000):
        self.server = server
        self.timeout = Timeout(timeout)
        self.result = None
        try:
            address = socket.getaddrinfo(self.server, 123)[0][-1]
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            self.socket.sendto(b'\x1b' + 47 * b'\0', address)
        except:
            self.socket = None

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def _recv(self):
        try:
            msg, address = self.socket.recvfrom(17 * 4)
            self.close()
        except:
            if self.timeout.expired():
                self.close()
            return
        try:
            t = struct.unpack_from("!I", msg, 40)[0] or None
            # TODO: NTP timestamp will overflow in 2036; apply temporary fix for another 100 years.
            if t < 3870000000:
                t += 2**32
            # TODO: time.localtime will overflow in 2038; just hope that MicroPython has it fixed by then.
            t = time.localtime(t - 2208988800)
            # TODO: Check sane result compared to RTC
            self.result = (t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0)
        except:
            self.result = False
        return True

    def done(self):
        return not self.socket or self._recv()

    def datetime(self):
        return self.done() and self.result

    def wait(self, any = False):
        while not self.done():
            continue
        return self.datetime()

class WebSyncRTC:
    def __init__(self, server = "pool.ntp.org", interval = 86400_000):
        self.server = server
        self.interval = interval
        self.timer = Timeout(-1)
        self.ntp = None
        self.synced = None

    def __call__(self, request):
        # Support WebMain module interface.
        self.ntp = self.ntp or (self.timer.expired() and SimpleNTPClient(self.server))
        if self.ntp and self.ntp.done():
            t = self.ntp.datetime()
            self.ntp = None
            if t:
                machine.RTC().datetime(t)
                self.timer = Timeout(self.interval)
                self.synced = "{0:04}-{1:02}-{2:02}T{3:02}:{4:02}:{5:02}Z".format(*t[0:3], *t[4:7])
                print(f"NTP synced: {self.synced}")
            else:
                self.timer = Timeout(10_000)
        if request and not request.path_info:
            request.reply(f"Last NTP sync: {self.synced}, from {self.server}, interval {self.interval} ms")
