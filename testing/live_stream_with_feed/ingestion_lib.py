from lib import Handler, Request, FrameBuffer

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


class ServerHandler(Handler):
    """
    Initialized for every incoming connection to the server
    Should be able to handle any stream type
    """
    def __init__(self, *args):
        super().__init__(*args)

        self.frames_sent = 0
        self.frames_received = 0
        self.parent.frame_buffer = FrameBuffer()

    def INGEST_VIDEO(self, request):
        """ Handle image data received from Pi """
        frame = request.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(request.header['frames-sent'])
        diff = abs(self.frames_sent - self.frames_received)
        if diff > 10:
            self.log("Warning: Some frames were lost ({})".format(diff))

        # write current frame to the server's frame-buffer so that it can be sent with a different connection handler
        self.parent.frame_buffer.write(frame)
        self.debug("ingested video")

    def GET(self, request):
        """ Handle request from web browser """
        self.debug("Received Web Browser Request")
        response = Request()

        if request.path == '/':
            self.debug("Handling request for '/'. Redirected to index.html")
            response.add_response(301)  # redirect
            response.add_header('Location', '/index.html')  # redirect to index.html
            self.send(response)

        elif request.path == '/favicon.ico':
            self.debug("Handling request for favicon")
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                img = fout.read()
                response.add_content(img)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'image/x-icon')  # favicon
            response.add_header('Content-Length', len(img))
            self.send(response)

        elif request.path == '/index.html':
            self.debug("Handling request for /index.html, sending page html")
            content = PAGE.encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_header('Content-Length', len(content))
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path == '/stream.mjpg':
            self.debug("Handling request for stream.mjpeg")
            self.send_multipart(self.parent.frame_buffer, 'image/jpeg', 'FRAME')
        else:
            response.add_response(404)  # couldn't find it
            self.send(response)
            self.debug("GET requested unknown path", "path: {}".format(request.path))

        self.debug("done handling GET")
