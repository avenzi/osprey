from lib import ServerHandler


class Handler(ServerHandler):
    """
    Initialized for every incoming connection to the server
    Should be able to handle any stream type
    """
    def __init__(self, *args):
        super().__init__(*args)

        self.frames_sent = 0
        self.frames_received = 0

    def INGEST_VIDEO(self, request):
        """ Handle image data received from Pi """
        frame = request.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(request.header['frames-sent'])
        diff = abs(self.frames_sent - self.frames_received)
        if diff > 10:
            self.log("Warning: Some frames were lost ({})".format(diff))

        # write current frame to the server's frame-buffer so that it can be sent with a different connection handler
        self.frame_buffer.write(frame)
        self.debug("ingested video")
