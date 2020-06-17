import io
import picamera
import socket
from threading import Condition
from time import sleep, strftime
from lib import StreamBase


class StreamClient(StreamBase):
    def __init__(self, ip, port, resolution='640x480', framerate=24, debug=False):
        super().__init__(ip, port, debug)

        self.camera = None              # picam object
        self.resolution = resolution    # resolution of stream
        self.framerate = framerate      # camera framerate
        self.output = None              # file-like object buffer for the camera to stream to

    def setup(self):
        """ Create socket and connect to server ip """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        self.log("Socket Created")

        try:  # connect socket to given address
            self.log("Attempting to connect to {}:{}".format(self.ip, self.port))
            self.socket.connect((self.ip, self.port))
            self.log("Socket Connected")
        except Exception as e:
            self.error("Failed to connect to server", e)

    def stream(self):
        self.start_recording()
        msg = False  # flag for displaying the streaming notification
        while not self.exit:  # run until exit status is set
            self.send_images()
            if self.frames_sent == 1 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')

    def send_images(self):
        """ Handle sending images to the stream """
        with self.output.condition:
            self.output.condition.wait()
            frame = self.output.frame  # get next frame from picam

        self.frames_sent += 1
        self.add_header("content-length", len(frame))
        self.add_header("frames-sent", self.frames_sent)
        self.send_headers()
        self.send_content(frame)

    def finish(self):
        """ Executes on termination """
        self.stop_recording()  # stop recording

    def start_recording(self):
        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.output = StreamOutput()  # file-like output object for the picamera to write to
        self.camera.start_recording(self.output, format='mjpeg')
        self.log("Started Recording: {}".format(strftime('%Y/%m/%d %H:%M:%S')))
        sleep(2)

    def stop_recording(self):
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(strftime('%Y/%m/%d %H:%M:%S')))


class StreamOutput(object):
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