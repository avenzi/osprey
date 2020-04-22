import threading
import socketserver
import http.server
from http.server import HTTPServer, BaseHTTPRequestHandler
from database import Database

class Listener(BaseHTTPRequestHandler):
    def ensure_database_connection(self):
        try:
            x = self.db_connection
        except Exception:
            # Set up Database Connection
            self.db_connection, self.cursor = Database().get_connection()

    def do_GET(self):
        pass

    def do_POST(self):
        content_length = int(self.headers["Content-Length"]) # gets the size of data being sent in the request
        data = self.rfile.read(content_length)

        self.ensure_database_connection()

        # pass the request to the child
        self.post_request(self.headers, data)

        # send response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"response")


