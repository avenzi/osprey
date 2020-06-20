from lib import Base, ServerConnectionBase, FrameBuffer, Address
from requests import get

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


class Server(Base):
    """
    Handles incoming connections
    """
    def __init__(self, port, ip='', name='Server', debug=False):
        super().__init__(debug)
        self.ip = ip
        self.port = port
        self.name = name

    def serve(self):
        """ Listens for new connections, then starts then on their own thread """
        self.log("IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        while True:
            conn = ServerConnection(self.ip, self.port, self.name, self.debug_mode)
            conn.run()  # wait for connection then start handling on a new thread


class ServerConnection(ServerConnectionBase):
    """
    Initialized for every incoming connection to the server
    Should be able to handle any stream type
    """
    def __init__(self, ip, port, name, debug):
        super().__init__(ip, port, name, debug)

        self.frames_sent = 0
        self.frames_received = 0
        self.frame_buffer = FrameBuffer()

    def start(self):
        """ Executes on startup """
        self.add_request('START')
        self.send_headers()

    def finish(self):
        """ Executes before termination """
        self.log("Frames Received: {}/{}".format(self.frames_received, self.frames_sent))

    def INGEST_VIDEO(self):
        """ Handle image data received from Pi """
        frame = self.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(self.header['frames-sent'])
        diff = abs(self.frames_sent - self.frames_received)
        if diff > 10:
            self.log("Warning: Some frames were lost ({})".format(diff))

        # write current frame to buffer so that it can be sent to a web browser feed
        self.frame_buffer.write(frame)

    def GET(self):
        """ Handle request from web browser """
        self.debug("Received Web Browser Request")

        if self.path == '/':
            self.log("Handling request fore '/'. Redirected to index.html", level='debug')
            self.add_response(301)  # redirect
            self.add_header('Location', '/index.html')  # redirect to index.html
            self.send_headers()

        elif self.path == '/favicon.ico':
            self.log("Handling request for favicon")
            self.add_response(200)  # success
            self.add_header('Content-Type', 'image/x-icon')  # favicon
            self.send_headers()
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                data = fout.read()
                print(type(data))
                self.send_content(fout.read())

        elif self.path == '/index.html':
            self.log("Handling request for /index.html, sending page html", level='debug')
            content = PAGE.encode(self.encoding)
            self.add_response(200)  # success
            self.add_header('Content-Type', 'text/html')
            self.add_header('Content-Length', len(content))
            self.send_headers()
            self.send_content(content)  # write html content to page

        elif self.path == '/stream.mjpg':
            self.log("Handling request for stream.mjpeg", level='debug')
            self.add_response(200)  # success
            self.add_header('Age', 0)
            self.add_header('Cache-Control', 'no-cache, private')
            self.add_header('Pragma', 'no-cache')
            self.add_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.send_headers()
            try:
                while True:  # continually write individual frames to page
                    with self.frame_buffer.condition:
                        self.frame_buffer.condition.wait()
                        frame = self.frame_buffer.frame
                    self.send_content(b'--FRAME\r\n')
                    self.add_header('Content-Type', 'image/jpeg')
                    self.add_header('Content-Length', len(frame))
                    self.send_headers()
                    self.send_content(frame)
            except Exception as e:
                self.error('Browser Stream Disconnected ({})'.format(self.client), e)
        else:
            #self.send_error(404)  # couldn't find it
            #self.end_headers()
            self.debug("GET request not accounted for")
            return
