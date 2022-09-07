"""This is an example on how to use WebMain.

 - Write module as a function or an object with __call__ method.
   It will be passed a WebRequest object when a request arrives.
   See WebMain.__call__ and other __call__ methods for examples.

 - Write a main class similar to ExampleMain, derived from WebMain.
   All custom configuration should be done inside __init__.
   Remember to call super().__init__ with proper options.
   Add modules with add_module(handler, name_for_listing, uri).
   Start the server with MainClass.main().
"""

class ExampleModule:
    def __call__(self, request):
        # Error pages (content = "when empty page is not enough").
        if request.method != "GET":
            return request.reply(status = 404)

        # Custom content types.
        if request.path_info == "?json":
            return request.reply(mime = b"application/json", content = "[1,2,3]")

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
        # Import your own modules: from Example import ExampleModule

        # Start WLAN and initialize WebMain.
        # Needs wlan.conf: {"ssid": "MyNet", "key": "my-secrets", "ap": false}
        network = SimpleWLAN.from_config()
        super().__init__(network)

        # Add the default front page to another uri, if you wish.
        self.add_module(self, uri = "/WebMain")

        # Add a module with default uri (which is "/" + __name__).
        self.add_module(ExampleModule())

        # Add a module with custom uri.
        # If you use "/", it must be last.
        self.add_module(ExampleModule(), uri = "/")

# Start the web server.
ExampleMain.main()
