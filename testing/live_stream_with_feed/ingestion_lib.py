from lib import Handler, Request, DataBuffer

# html for the web browser stream
PAGE = """\
<html>
<head><title>Picam</title></head>
<body>
    <h1>RasPi MJPEG Streaming</h1>
    <img src="stream.mjpg" width="500" height="500" />
</body>
</html>
"""
# TODO: figure out how to force the size of the image to be constant but keep the original aspect ratio.
# This would be so that the resolution only has to be adjusted in one location - the client video handler class.
# Ideally, this html would be able to handle any image without needing to be modified.


class ServerHandler(Handler):
    """
    Initialized for every incoming connection to the server
    Should be able to handle any stream type
    """
    def __init__(self, *args):
        super().__init__(*args)

        self.frames_sent = 0
        self.frames_received = 0
        self.parent.frame_buffer = DataBuffer()

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
            self.debug("Handling request for '/'. Redirecting to index.html", 3)
            response.add_response(301)  # redirect
            response.add_header('Location', '/index.html')  # redirect to index.html
            self.send(response)

        elif request.path == '/favicon.ico':
            self.debug("Handling request for favicon", 3)
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                img = fout.read()
                response.add_content(img)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'image/x-icon')  # favicon
            response.add_header('Content-Length', len(img))
            self.send(response)

        elif request.path == '/index.html':
            self.debug("Handling request for /index.html, sending page html", 3)
            content = PAGE.encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_header('Content-Length', len(content))
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path == '/stream.mjpg':
            self.debug("Handling request for stream.mjpeg", 2)
            self.send_multipart(self.parent.frame_buffer, 'image/jpeg', 'FRAME')
        else:
            response.add_response(404)  # couldn't find it
            self.send(response)
            self.error("GET requested unknown path", "path: {}".format(request.path))

        self.debug("done handling GET", 2)
