"""Very simplified asynchronous implementation of ping."""

import socket, struct, time
from Timeout import Timeout

def checksum(data):
    """Internet checksum"""
    s = 0
    for i in range(len(data)):
        s += data[i] << (0 if i & 1 else 8)
        if s > 0xffff:
            s -= 0xffff
    return s ^ 0xffff

class SimplePing:
    """Ping a host

    Synchronous ping:
    ping_ms = SimplePing(host, timeout = ms).wait()

    Asynchronous ping; resolution depends on poll interval!
    p = SimplePing(host, timeout = ms)
    while not p.done():
        do_other_stuff()
    ping_ms = p.ms()
    """

    def __init__(self, host, count = 5, interval = 100, timeout = 1000):
        self.host = host
        self.count = count
        self.interval = interval
        self.timeout = timeout
        self.ping_size = 64
        self.ping_id = time.ticks_us() & 0xffff
        self.ping_seq = 0
        self.pong_ms = None
        self.pong_seq_max = 0
        self._recv_timeout = Timeout(0)
        self._done = False
        self.socket = None
        self.broken = False
        self._ping()

    def _connect(self):
        try:
            address = socket.getaddrinfo(self.host, 1)[0][-1]
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, 1)
            self.socket.setblocking(False) # select.poll returns POLLHUP with SOCK_RAW.
            self.socket.connect(address)
            return True
        except OSError as e:
            self.socket and self.socket.close()
            self.socket = None
            if e.errno == 12: # ENOMEM
                self.broken = True

    def _ping(self):
        self.ping_seq += 1
        self._send_timeout = Timeout(self.interval)
        if not self.socket and not self._connect():
            return
        packet = bytearray(self.ping_size)
        struct.pack_into("!BBHHHQ", packet, 0, 8, 0, 0, self.ping_id, self.ping_seq, time.ticks_ms())
        struct.pack_into("!H", packet, 2, checksum(packet))
        try:
            self.socket.send(packet)
        except OSError as e:
            return # Mostly EHOSTUNREACH (113)
        self._recv_timeout = Timeout(self.timeout)

    def _pong(self):
        if not self.socket:
            return False
        try:
            ip_packet = self.socket.recv(20 + self.ping_size)
            p_type, _, _, p_id, p_seq, p_time = struct.unpack_from("!BBHHHQ", ip_packet, 20)
        except:
            return False
        if p_type == 0 and p_id == self.ping_id:
            if p_seq > self.pong_seq_max:
                self.pong_seq_max = p_seq
                p_ms = time.ticks_diff(time.ticks_ms(), p_time)
                if p_ms <= (self.pong_ms or self.timeout):
                    self.pong_ms = p_ms or 1 # For simplicity, never return zero.
        return True

    def update(self):
        if not self._done:
            if self.ping_seq < self.count and self._send_timeout.expired():
                self._ping()
            while self._pong():
                continue
            if self.ping_seq >= self.count and self._recv_timeout.expired():
                self.close()

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self._done = True

    def done(self):
        self.update()
        return self._done

    def ms(self):
        self.update()
        return self.pong_ms

    def wait(self, any = False):
        while not self.done():
            continue
        return self.ms()
