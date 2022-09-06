"""This is an example on how to use WebMain.

 - Write a main class similar to ExampleMain, derived from WebMain.
   All custom configuration should be done inside __init__.
   Remember to call super().__init__ with proper options.
   Start the server with MainClass.main().
"""

from WebMain import WebMain
class ExampleMain(WebMain):
    def __init__(self):
        # Import modules.
        from SimpleWLAN import SimpleWLAN

        # Start WLAN and initialize WebMain.
        # Needs wlan.conf: {"ssid": "MyNet", "key": "my-secrets", "ap": false}
        network = SimpleWLAN.from_config()
        super().__init__(network)

# Start the web server.
ExampleMain.main()
