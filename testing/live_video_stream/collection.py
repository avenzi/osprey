import picamera
import struct
from time import strftime
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
                self.condition.notify_all()  # notify all clients that it's available
            self.buffer.seek(0)
        return self.buffer.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    """ Passed into StreamingServer to handle requests """
            
    def do_CLIENTSTREAM(self):
        """
        Streams data to the ingestion client.
        Activated when the custom request mathod CLIENTSTREAM is sent.
        Named do_CLIENTSTREAM because the inherited handler class uses the
            received method to call functions of the form do_METHODNAME()
        """
        ip, port = self.client_address
        print("Streaming to Ingestion Client ({}:{})".format(ip, port))

        try:
            number = 0  # number of frames sent
            while True:  # write individual frames
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                number += 1
                header = {'length': len(frame), 'number': number} 
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
            print('Ingestion Stream Disconnected ({}:{}) -- {}'.format(ip, port, str(e)))
        
        
    def do_GET(self):
        """ Handles stream requests from a web browser """
        ip, port = self.client_address
        print("Streaming to Web Browser ({}:{})".format(ip, port))
        
        # Set page headers based on location
        if self.path == '/':
            self.send_response(301)  # redirect
            self.send_header('Location', '/index.html')  # redirect to index.html
            self.end_headers()
        elif self.path == '/favicon.ico':
            self.send_response(200)  # success
            self.send_header('Content-Type', 'image/x-icon')  # favicon
            self.end_headers()
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                self.wfile.write(fout.read())
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')  # encode html string
            self.send_response(200)  # success
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)  # write html content to page
        elif self.path == '/stream.mjpg':
            self.send_response(200)  # success
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:  # continually write individual frames to page
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
                print('Browser Stream Disconnected ({}:{}) -- {}'.format(ip, port, str(e)))
        else:
            self.send_error(404)  # couldn't find it
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """ Server class that will call serve_forever() in collection.py """
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()  # file-like output
    camera.start_recording(output, format='mjpeg')
    print("Started Recording:", strftime('%Y/%m/%d %H:%M:%S'))

    try:
        address = ('', PORT)
        server = StreamingServer(address, StreamingHandler)
        ip = get('http://ipinfo.io/ip').text.replace('\n','')
        print("Starting Server:  {}:{}".format(ip, PORT))
        server.serve_forever()  # start server
    finally:
        camera.stop_recording()  # stop recording on error or termination
        print("Stopped Recording:", strftime('%Y/%m/%d %H:%M:%S'))
