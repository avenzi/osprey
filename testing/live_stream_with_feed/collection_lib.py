import picamera
from time import sleep
from lib import ClientHandler, Request


class VideoClientHandler(ClientHandler):
    def __init__(self, *args):
        super().__init__(*args)

        self.camera = None             # picam object
        self.resolution = '640x480'    # resolution of stream
        self.framerate = 24            # camera framerate

        self.frames_sent = 0    # number of frames sent
        self.active = False     # toggles stream

        # Send info to server
        self.init(framerate=self.framerate, resolution=self.resolution)

    def START(self, request):
        """ Start Streaming continually."""
        if self.active:
            self.log("Stream already Started")
            return

        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.camera.start_recording(self.data_buffer, format='mjpeg')
        self.log("Started Recording: {}".format(self.date()))
        sleep(2)
        self.log("Started Stream...")

        self.active = True
        while self.active:  # stream until toggled
            frame = self.data_buffer.read()
            self.frames_sent += 1
            
            response = Request()  # new request object to send
            response.add_request('INGEST_VIDEO')
            response.add_header("content-length", len(frame))
            response.add_header("frames-sent", self.frames_sent)
            response.add_content(frame)
            self.send(response)  # send request to outgoing buffer

    def STOP(self, request):
        """ Request method STOP """
        self.active = False
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(self.date()))
        self.log("Stopped Stream.")
