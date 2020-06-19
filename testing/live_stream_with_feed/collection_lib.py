import io
import picamera
from time import sleep
from lib import ClientConnectionBase, FrameBuffer


class VideoClient(ClientConnectionBase):
    def __init__(self, ip, port, name='Client', resolution='640x480', framerate=24, debug=False):
        super().__init__(ip, port, name, debug)

        self.camera = None                # picam object
        self.resolution = resolution      # resolution of stream
        self.framerate = framerate        # camera framerate
        self.frame_buffer = FrameBuffer   # file-like object buffer for the camera to stream to

        self.frames_sent = 0              # number of frames sent

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
        with self.output.condition:
            self.output.condition.wait()
            frame = self.output.frame  # get next frame from picam

        self.frames_sent += 1
        self.send_request_line('INGEST')
        self.add_header("content-length", len(frame))
        self.add_header("frames-sent", self.frames_sent)
        self.add_header("client-name", self.name)
        self.send_headers()
        self.send_content(frame)

    def START(self):
        """ Request method START """
        msg = False  # flag for displaying the streaming notification
        while not self.exit:  # run until exit status is set
            self.send_images()
            if self.frames_sent == 1 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')
