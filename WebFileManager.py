import json, machine, os, time

class WebFileManager:
    """File manager module; remember to include the .html file!"""

    def _try(self, request, action):
        try:
            action()
        except:
            request.reply(status = 500, content = b"fail")
        else:
            request.reply(status = 200, content = b"ok")

    def _write(self, name, request):
        with open(name, "wb") as f:
            request.request_body_callback(lambda data: f.write(data))

    def __call__(self, request):
        if not request:
            return
        method = request.method
        query = request.path_info
        if query and not query.startswith("?"):
            return

        if method == "GET" and query == "":
            return request.reply_static("WebFileManager.html")

        if method == "GET" and query.startswith("?ls="):
            try:
                name = query.split("=", 1)[1]
                data = json.dumps([i[0] if i[1] != 0x4000 else i[0] + "/" for i in os.ilistdir(name)])
            except:
                return request.reply(status = 404)
            else:
                return request.reply(data)

        if method == "GET" and query.startswith("?read="):
            try:
                return request.reply_static(query.split("=", 1)[1])
            except:
                return

        if method == "POST" and query.startswith("?write="):
            return self._try(request, lambda: self._write(query.split("=", 1)[1], request))

        if method == "POST" and query.startswith("?mkdir="):
            return self._try(request, lambda: os.mkdir(query.split("=", 1)[1]))

        if method == "POST" and query.startswith("?rmdir="):
            return self._try(request, lambda: os.rmdir(query.split("=", 1)[1]))

        if method == "POST" and query.startswith("?unlink="):
            return self._try(request, lambda: os.unlink(query.split("=", 1)[1]))

        if method == "POST" and query.startswith("?reset"):
            request.reply(b"ok")
            request.socket.close()
            time.sleep_ms(100)
            machine.reset()
