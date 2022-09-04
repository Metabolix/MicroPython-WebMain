import time

class Timeout:
    """Track time: init x = Timeout(ms), check x.expired()"""

    def __init__(self, ms):
        self.ms = ms
        self.started = time.ticks_ms()

    def expired(self):
        return self.ms and time.ticks_diff(time.ticks_ms(), self.started) > self.ms
