"""This is an example on how to use WebMain.

 - Write module as a function or an object with __call__ method.
   It will be passed a WebRequest object when a request arrives.
   It will be passed None periodically to allow background tasks.
   See WebMain.__call__ and other __call__ methods for examples.

 - Write a main class similar to ExampleMain, derived from WebMain.
   All custom configuration should be done inside __init__.
   Remember to call super().__init__ with proper options.
   Add modules with add_module(handler, name_for_listing, uri).
   Add static pages with add_static(path, uri).
   Start the server with MainClass.main().
"""

class ExampleModule:
    def __call__(self, request):
        # When request is None, run any background tasks.
        if not request:
            return

        # Error pages (content = "when empty page is not enough").
        if request.method != "GET":
            return request.reply(status = 404)

        # Custom content types.
        if request.path_info == "?json":
            return request.reply(mime = b"application/json", content = "[1,2,3]")

        # Static content, with automatic MIME types for some common extensions.
        if request.path_info == "/image.jpg":
            return request.reply_static("path-to-image.jpg")

        # Static content, with custom MIME type.
        if request.path_info == "/audio.webm":
            return request.reply_static("audio.webm", mime = b"audio/webm")

        # Default: plain text, unless you set mime = b"...".
        request.reply(
            f"{self.__class__.__name__}: {request.method} {request.uri}\n" +
            f"module uri: {request.script_name}\n" +
            f"remaining uri to handle: {request.path_info}\n"
        )

from WebMain import WebMain
class ExampleMain(WebMain):
    def __init__(self):
        # Import modules.
        from SimpleWLAN import SimpleWLAN
        from WebFileManager import WebFileManager
        # Import your own modules: from Example import ExampleModule

        # Start WLAN and initialize WebMain.
        # Needs wlan.conf: {"ssid": "MyNet", "key": "my-secrets", "ap": false}
        network = SimpleWLAN.from_config()
        super().__init__(network)

        # Add any common static content (files or dirs).
        self.add_static("/favicon.ico")
        self.add_static("/static-pages")

        # Add the default front page to another uri, if you wish.
        self.add_module(self, uri = "/WebMain")

        # Add a module with default uri (which is "/" + __name__).
        self.add_module(WebFileManager())

        # Add a module with custom uri.
        # If you use "/", it must be last.
        self.add_module(ExampleModule(), uri = "/")

# Start the web server.
ExampleMain.main()
