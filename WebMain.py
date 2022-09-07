"""Web-based main loop for MicroPython. See Example.py for instructions."""

import socket, time, machine, sys, os, gc
from Timeout import Timeout

class WebRequest:
    def __init__(self, socket):
        self.socket = socket
        self.output_started = False

    def parse(self):
        self.socket.setblocking(True)
        head = bytearray()
        while True:
            s = self.socket.readline()
            if not s or not s.strip():
                break
            head.extend(s)
        head = head.strip()
        raw_headers = head.decode().split("\r\n")
        self.method, self.uri, self.http_version = raw_headers[0].split(" ")

    def reply(self, content = b"", status = 200, mime = b"text/plain; charset=UTF-8"):
        if not self.output_started:
            status = str(status).encode()
            if type(mime) == str:
                mime = mime.encode()
            self.socket.send(b"HTTP/1.0 " + status + b" -\r\nContent-Type: " + mime + b"\r\n\r\n")
            self.output_started = True
        if content:
            self.socket.send(content)

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

    def __init__(self, network, display_errors = True, front_page = True, background_interval = 2_000):
        self.network = network
        self.socket = None
        self.display_errors = display_errors
        self.front_page = front_page
        self.modules = []
        self.background_interval = background_interval

    class WebModule:
        def __init__(self, name, uri, handler):
            self.name = name
            self.uri = uri
            self.handler = handler

    def add_module(self, handler, name = True, uri = True):
        if name is True:
            try:
                name = handler.__name__
            except:
                name = handler.__class__.__name__
        if uri is True:
            uri = "/" + name
        self.modules.append(self.WebModule(name, uri, handler))

    def _run(self):
        run_background_work = Timeout(-1)
        while True:
            if self.network.connected() and not self.socket:
                self._listen()
            if not self._accept_request() or run_background_work.expired():
                for module in self.modules:
                    module.handler(None)
                run_background_work = Timeout(self.background_interval)
            if not self._accept_request():
                time.sleep_ms(10)

    def _listen(self):
        print(f"Starting HTTP server http://{self.network.ip}/")
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(False)
        self.socket.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
        self.socket.listen(4)

    def _accept_request(self):
        try:
            client, client_address = self.socket.accept()
        except:
            return

        try:
            error = (401, b"Failed to parse request")
            request = WebRequest(client)
            request.parse()
            print(f"{request.method} {request.uri}")
            error = (500, b"Failed to process request")
            self._dispatch_request(request)
            if not request.output_started:
                request.reply(status = 404, content = b"Not found")
        except BaseException as e:
            sys.print_exception(e)
            try:
                if not request.output_started:
                    request.reply(status = error[0], content = error[1])
                if self.display_errors:
                    request.reply(b"\n\n")
                    sys.print_exception(e, client)
            except:
                pass
        finally:
            client.close()
        return True

    def _dispatch_request(self, request):
        for module in self.modules:
            if self._dispatch_request_if_matches(request, module.uri, module.handler):
                return
        if self.front_page:
            self._dispatch_request_if_matches(request, "/", self)

    def _dispatch_request_if_matches(self, request, script_name, handler):
        if script_name and request.uri.startswith(script_name):
            l = len(script_name)
            if (len(request.uri) <= l or request.uri[l] in "/?" or request.uri[l-1] in "/?"):
                request.script_name = script_name
                request.path_info = request.uri[l:]
                handler(request)
                return True

    def __call__(self, request):
        if not request:
            # Time to do any background work.
            return

        if request.path_info != "":
            # Page is not found.
            return

        gc.collect()
        uname = os.uname()
        request.reply(status = 200, mime = b"text/html; charset=UTF-8")
        request.reply(f"""<!DOCTYPE html>
            <title>WebMain on {uname.nodename}</title>
            <h1>WebMain on {uname.nodename}</h1>
            <p>machine: {uname.machine}</p>
            <p>version: {uname.version}</p>
            <p>reset_cause: {machine.reset_cause()}</p>
            <p>freq: {machine.freq()}</p>
            <p>mem: {gc.mem_alloc()} used, {gc.mem_free()} free</p>
            <h2>Modules</h2>
        """)
        for module in self.modules:
            if module.uri:
                request.reply(f"<li><a href='{module.uri}'>{module.name}</a>")
            else:
                request.reply(f"<li>{module.name}")
        if not self.modules:
            request.reply(b"<p>Oh no, you haven't configured any modules!</p>")
