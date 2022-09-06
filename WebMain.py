"""Web-based main loop for MicroPython. See Example.py for instructions."""

import socket, time, machine, sys
from Timeout import Timeout

class WebMain:
    @classmethod
    def main(self):
        retry_acceptable = None
        main = None
        try:
            # Use inheritance to customize & add modules.
            main = self()
            retry_acceptable = Timeout(240_000)
            main._run()
        except KeyboardInterrupt as e:
            sys.print_exception(e)
            return
        except BaseException as e:
            sys.print_exception(e)
            with open("WebMain.log", "a") as file:
                file.write(b"\n---------\n")
                sys.print_exception(e, file)
        finally:
            if main and main.socket:
                main.socket.close()
        if retry_acceptable and retry_acceptable.expired():
            machine.reset()

    def __init__(self, network):
        self.network = network
        self.socket = None

    def _run(self):
        while True:
            if self.network.connected() and not self.socket:
                self._listen()
            if not self.accept_request():
                time.sleep_ms(10)

    def _listen(self):
        print(f"Starting HTTP server http://{self.network.ip}/")
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(False)
        self.socket.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
        self.socket.listen(4)

    def accept_request(self):
        try:
            client, client_address = self.socket.accept()
        except:
            return

        try:
            client.setblocking(True)
            while client.readline().strip():
                continue
            client.send(b"HTTP/1.0 404 Not Found\r\n\r\nThis server has nothing to offer.")
        except BaseException as e:
            sys.print_exception(e)
        finally:
            client.close()
        return True
