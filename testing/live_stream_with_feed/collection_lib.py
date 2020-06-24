import io
import picamera
from time import sleep
import threading
from threading import Thread, Condition
from lib import Handler, Request


class VideoClientHandler(Handler):
    def __init__(self, *args):
        super().__init__(*args)

        self.camera = None                 # picam object
        self.resolution = '640x480'        # resolution of stream
        self.framerate = 24                # camera framerate
        self.frame_buffer = FrameBuffer()  # file-like object buffer for the camera to stream to

        self.frames_sent = 0    # number of frames sent
        self.active = False     # toggled by server to activate the stream

    def start(self):
        """ Executes on initialization """
        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.camera.start_recording(self.frame_buffer, format='mjpeg')
        self.log("Started Recording: {}".format(self.date()))
        sleep(2)

    def finish(self):
        """ Executes on termination """
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(self.date()))

    def START(self, request):
        """ Request method START. Start Streaming continually on a new thread."""
        if self.active:
            self.log("Stream already Started")
            return
        self.active = True  # activate stream
        self.log("Started Stream...")

        while self.active:  # stream until toggled
            with self.frame_buffer.condition:
                self.frame_buffer.condition.wait()
                frame = self.frame_buffer.frame  # get next frame from picam

            response = Request()  # new request object to send
            response.frames_sent += 1
            response.add_request('INGEST_VIDEO')
            response.add_header("content-length", len(frame))
            response.add_header("frames-sent", self.frames_sent)
            response.add_content(frame)
            self.send(response)  # send request to outgoing buffer

    def STOP(self, request):
        """ Request method STOP """
        self.active = False  # deactivate stream
        self.log("Stopped Stream...")


class FrameBuffer(object):
    """
    A thread-safe buffer to store frames in
    The write() method can be used by a Picam
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):  # jpeg image
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # wake any waiting threads
            self.buffer.seek(0)
        return self.buffer.write(buf)

