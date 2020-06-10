import io
import logging
import socketserver
from threading import Condition
from http import server

# html for the web browser stream
PAGE = """\
<html>
<head><title>Picam</title></head>
<body>
<h1>RasPi MJPEG Streaming</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""


class StreamingOutput(object):
    """
    Used by Picam's start_recording() method.
    Writes frames to a buffer to be sent to the client
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # notify all nclients it's available
            self.buffer.seek(0)
        return self.buffer.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    """ Passed into StreamingServer to handle requests """
    def do_GET(self):
        """ Handles requests from a web browser """
        # Set page headers based on location
        if self.path == '/':
            self.send_response(301)  # incorrect location
            self.send_header('Location', '/index.html')  # redirect to index.html
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)  # success
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)  # success
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:  # continually write individual frames
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s',self.client_address, str(e))
        else:
            self.send_error(404)  # couldn't find it
            self.end_headers()

    def handle(self):
        """ Handles requests from a direct TCP connection to the server (data ingestion) """
        try:
            while True:  # write individual frames
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                print('writing frame:', len(frame), frame)
                self.wfile.write(str(len(frame)).encode())  # send proto (length of header)
                self.wfile.write()
                self.wfile.write(frame)
                #self.wfile.write(b'\r\n')  # message terminator?
        except Exception as e:
            logging.warning(str(e))


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """ Server class that will call serve_forever() in collection.py """
    allow_reuse_address = True
    daemon_threads = True
