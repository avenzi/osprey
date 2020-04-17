import io
import picamera
import logging
import socketserver
import datetime
from threading import Condition
from http import server

epoch = datetime.datetime.utcfromtimestamp(0)
###########################################################
# Streaming Output class to support mjpeg stream
###########################################################
class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


############################################################
# Streaming Handler Class to serve each mjpg frame
############################################################
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            
            # Serve mjpg frame
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame

                    time = datetime.datetime.now()
                    timestamp = (time - epoch).total_seconds() * 1000.0
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.send_header('Timestamp', timestamp)
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        
        else:
            self.send_error(404)
            self.end_headers()



############################################################
# Streaming server class using Threading Mix In and HTTP Server packages
############################################################
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# Start camera recording
with picamera.PiCamera(resolution='640x480', framerate=16) as camera:
    output = StreamingOutput()
    # Change camera rotation  
    camera.rotation = 180
    camera.start_recording(output, format='mjpeg')
    
    # Serve until local error
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
