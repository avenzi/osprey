import io
import os
import picamera
import logging
import socketserver
from threading import Condition
from http import server
from requests import get

PORT = 8000  # port on which to host the stream

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
    """ Class passed into the picam's start_recording() method) """
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
                while True:  # write individual frames
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
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)  # couldn't find it
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    
    camera.start_recording(output, format='mjpeg')
    print("Started Recording")

    try:
        
        address = ('', PORT)
        server = StreamingServer(address, StreamingHandler)
        ip = get('http://ipinfo.io/ip').text.replace('\n','')
        print("Starting Server:  {}:{}".format(ip, PORT))
        server.serve_forever()
    finally:
        camera.stop_recording()  # stop recording on error or termination
        print("Stopped Recording.")
