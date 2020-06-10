import picamera
import struct
from requests import get

#from collection_lib import StreamingOutput, StreamingServer, StreamingHandler
from ingestion_lib import encode_json, decode_json

PORT = 8000  # port on which to host the stream

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
        print("raw get:", self.raw_requestline)
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
        # TODO: figure out how to run this code without overwriting handle()
        # the problem is that I can't seem to get this code to run within
        # the HTTPHandler without overwriting the handle() method, which
        # runs immediately when a request is received. However, the original
        # handle() method is what allows do_GET() to be called.
        # - Also figure out why moving these classes to a seaprate file causes
        # output to not be defined. Where does it come from anyway?
        # - Also figure out how to count number of images sent to track how many were lost
        # - Also whats the deal with favicon? I have one in the dir, but the server cant find it
        """ Handles requests from a direct TCP connection """
        try:
            while True:  # write individual frames
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                header = {'byteorder':'big', 'type':'image/jpeg', 'length': len(frame), 'encoding':'utf-8'} 
                header_bytes = encode_json(header, 'utf-8')  # header
                proto_bytes = struct.pack('>H', len(header_bytes))  # proto-header, big unsigned short
                self.wfile.write(proto_bytes)  # send proto (length of header)
                self.wfile.write(header_bytes)
                self.wfile.write(frame)
                #print('Proto:', proto_bytes, len(header_bytes))
                #print('Header:', header_bytes)
                #print('Frame:', frame)
                #self.wfile.write(b'\r\n')  # message terminator?
        except Exception as e:
            logging.warning(str(e))


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """ Server class that will call serve_forever() in collection.py """
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
