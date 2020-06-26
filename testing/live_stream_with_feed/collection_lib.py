import picamera
from time import sleep
from threading import Thread
from lib import Handler, Request, FrameBuffer


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

        t = Thread(target=self.START, daemon=True)
        t.start()  # call on startup.
        # If this ever changes and is instead called by a request, be sure to include the request object in the method declaration.

    def finish(self):
        """ Executes on termination """
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(self.date()))
        
    def START(self):
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

            self.frames_sent += 1
            
            response = Request()  # new request object to send
            response.add_request('INGEST_VIDEO')
            response.add_header("content-length", len(frame))
            response.add_header("frames-sent", self.frames_sent)
            response.add_content(frame)
            
            self.send(response)  # send request to outgoing buffer

    def STOP(self, request):
        """ Request method STOP """
        self.active = False  # deactivate stream
        self.log("Stopped Stream...")
