# Credit to StackOverflow user "personal_cloud"
# https://stackoverflow.com/a/46228009/7207297

import threading
from http.server import HTTPServer


class ServerThread(threading.Thread):
    def __init__(self, address, handler, sock):
        super().__init__()
        self.address = address
        self.handler = handler
        self.sock = sock
        self.httpd = HTTPServer(self.address, self.handler, False)
        self.daemon = True
        self.start()

    def run(self) -> None:

        # Prevent the HTTP server from re-binding every handler.
        # https://stackoverflow.com/questions/46210672/
        self.httpd.socket = self.sock
        self.httpd.server_bind = self.server_close = lambda self: None

        self.httpd.running = True
        self.httpd.serve_forever()

    def shutdown(self):
        self.httpd.running = False
        threading.Thread(target=self.httpd.shutdown).start()
