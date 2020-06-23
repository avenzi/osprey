import io
import picamera
from time import sleep
from threading import Thread
from lib import Handler


class VideoClientHandler(Handler):
    def __init__(self, ip, port, name='Client', resolution='640x480', framerate=24, debug=False):
        super().__init__(ip, port, name, False, debug)

        self.camera = None                 # picam object
        self.resolution = resolution       # resolution of stream
        self.framerate = framerate         # camera framerate
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
    
    def send_images(self):
        """ Handle sending images to the stream """
        while self.active:  # stream until toggled
            with self.frame_buffer.condition:
                self.frame_buffer.condition.wait()
                frame = self.frame_buffer.frame  # get next frame from picam

            self.frames_sent += 1
            self.add_request('INGEST_VIDEO')
            self.add_header("content-length", len(frame))
            self.add_header("frames-sent", self.frames_sent)
            self.end_headers()
            self.add_content(frame)

    def START(self):
        """ Request method START. Start Streaming continually on a new thread."""
        if self.active:
            self.log("Stream already Started")
            return
        self.active = True  # activate stream
        stream_thread = Thread(target=self.send_images, name="Stream-Thread", daemon=True)
        stream_thread.start()
        self.log("Started Stream...")

    def STOP(self):
        """ Request method STOP """
        self.active = False  # deactivate stream
        self.log("Stopped Stream...")
