"""Web-based main loop for MicroPython. See Example.py for instructions."""

import socket, select, time, machine, sys, os, gc
from Timeout import Timeout

def utc_time_str():
    return "{0:04}-{1:02}-{2:02}T{3:02}:{4:02}:{5:02}Z".format(*time.gmtime())

class WebRequest:
    def __init__(self, socket):
        self.socket = socket
        self.output_started = False
        self._data_pos = 0

    def _poll(self, event, *, ready, action):
        socket = self.socket
        socket.setblocking(False)
        poller = select.poll()
        poller.register(socket, event)
        while not ready():
            for x in poller.poll(2000):
                if x[1] & event:
                    action(socket)
                    break
            else:
                socket.close()
                return False

    def _recv(self, data, *, ready):
        self._poll(select.POLLIN, ready = ready, action = lambda socket: data.extend(socket.recv(1024)))

    def parse(self):
        data = bytearray()
        self._recv(data, ready = lambda: b"\r\n\r\n" in data)
        head, self._data = data.split(b"\r\n\r\n", 1)
        raw_headers = head.decode().split("\r\n")
        self.method, self.uri, self.http_version = raw_headers[0].split(" ")
        self.headers = []
        self.size = 0
        for row in raw_headers[1:]:
            name, value = row.split(":", 1)
            name, value = name.lower(), value.strip()
            self.headers.append((name, value))
            if name == "content-length":
                self.size = int(value)

    def request_body_callback(self, callback):
        while self._data_pos < self.size:
            if not self._data:
                self._recv(self._data, ready = lambda: len(self._data) > 0)
                if not self._data:
                    raise RuntimeError("Client disconnected or timed out.")
            self._data_pos += len(self._data)
            callback(self._data)
            self._data = bytearray()

    def _send(self, data):
        mem = memoryview(data)
        self.output_started = True
        data_i = 0
        def f(socket):
            nonlocal data_i
            data_i += socket.send(mem[data_i:])
        self._poll(select.POLLOUT, ready = lambda: data_i >= len(mem), action = f)

    def reply(self, content = b"", status = 200, mime = b"text/plain; charset=UTF-8"):
        if not self.output_started:
            status = str(status).encode()
            if type(mime) == str:
                mime = mime.encode()
            self._send(b"HTTP/1.0 " + status + b" -\r\nContent-Type: " + mime + b"\r\n\r\n")
        if content:
            self._send(content)

    def reply_static(self, path, mime = None):
        try:
            with open(path, "rb") as f:
                try:
                    ext = path[path.rindex(".", 1) + 1:]
                    self.reply(mime = mime or self._ext_to_mime[ext])
                except:
                    data = f.read(1024)
                    try:
                        data.decode("UTF-8")
                        self.reply(mime = b"text/plain; charset=UTF-8")
                    except:
                        self.reply(mime = b"application/octet-stream")
                    self.reply(data)
                    del data
                while True:
                    data = f.read(1024)
                    if not data:
                        return
                    self.reply(data)
        except:
            pass

    _ext_to_mime = {
        "html": b"text/html; charset=UTF-8",
        "css": b"text/css; charset=UTF-8",
        "js": b"text/javascript; charset=UTF-8",
        "png": b"image/png",
        "jpg": b"image/jpeg",
        "ico": b"image/x-icon",
        "svg": b"image/svg+xml",
        "webp": b"image/webp",
    }

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
            self._log(e)
        finally:
            if main and main.socket:
                main.socket.close()
        if retry_acceptable and retry_acceptable.expired():
            machine.reset()

    @classmethod
    def _log(self, e):
        sys.print_exception(e)
        with open("WebMain.log", "a") as file:
            file.write(f"\n---------\n{utc_time_str()}\n")
            sys.print_exception(e, file)

    def __init__(
        self, network,
        display_errors = True, front_page = True,
        background_interval = 2_000,
        ntp = True,
    ):
        self.network = network
        self.socket = None
        self.display_errors = display_errors
        self.front_page = front_page
        self.modules = []
        self.background_interval = background_interval
        if ntp:
            from SimpleNTPClient import WebSyncRTC
            self.add_module(WebSyncRTC())

    class WebModule:
        def __init__(self, name, uri, handler):
            self.name = name
            self.uri = uri
            self.handler = handler
            self.background = True

    def add_module(self, handler, name = True, uri = True):
        if name is True:
            try:
                name = handler.__name__
            except:
                name = handler.__class__.__name__
        if uri is True:
            uri = "/" + name
        self.modules.append(self.WebModule(name, uri, handler))

    def add_static(self, path, uri = True):
        if uri is True:
            uri = path
        handler = lambda request: self._handle_static(request, path)
        self.add_module(handler, "static: " + uri, uri)

    def _run(self):
        run_background_work = Timeout(-1)
        while True:
            if self.network.connected() and not self.socket:
                self._listen()
            if not self._accept_request() or run_background_work.expired():
                for module in self.modules:
                    try:
                        module.background and module.handler(None)
                    except KeyboardInterrupt as e:
                        raise e
                    except BaseException as e:
                        self._log(e)
                        module.background = False
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
            print(f"{utc_time_str()} {request.method} {request.uri}")
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

    def _handle_static(self, request, path):
        if not request:
            return
        if request.path_info and "../" in request.path_info:
            return
        request.reply_static(path + request.path_info)

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
            <p>time: {utc_time_str()} (UTC)</p>
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
