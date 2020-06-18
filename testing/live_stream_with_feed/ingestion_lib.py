import socket
import select
from requests import get
from lib import StreamBase

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


class StreamServer(StreamBase):
    def __init__(self, port, debug=False):
        super().__init__('', port, debug)  # accept any ip on this port

    def setup(self):
        """ Create socket and bind to local address then wait for connection from client """
        self.log("IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        self.log("Socket Created")

        try:  # Bind socket to ip and port
            #self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address
            sock.bind((self.ip, self.port))  # accept any ip on this port
            if self.ip == '':
                self.log("Socket Bound to *:{}".format(self.port))
            else:
                self.log("Socket Bound to {}:{}".format(self.ip, self.port))
        except Exception as e:
            self.error("Failed to bind socket to {}:{}".format(self.ip, self.port), e)

        try:  # Listen for connection
            self.log("Listening for Connection...")
            sock.listen()
        except Exception as e:
            self.error("Error while listening on {}:{}".format(self.ip, self.port), e)

        try:  # Accept connection. Accept() returns a new socket object that can send and receive data.
            self.socket, (self.pi_ip, self.pi_port) = sock.accept()
            self.socket.setblocking(False)  # non-blocking means that socket.recv() doesn't hang if no data is sent
            self.log("Accepted Connection From {}:{}".format(self.pi_ip, self.pi_port))
        except Exception as e:
            self.error("Failed to accept connection from {}:{}".format(self.pi_ip, self.pi_port), e)

        # if self.timeout is not None:  # is this needed?
        #    self.socket.settimeout(self.timeout)



    def stream(self):
        """ Read from the TCP continually, disconnecting on error. """
        msg = False  # flag for displaying the streaming notification
        while not self.exit:  # run until exit status is set
            self.handle()  # parse and handle all incoming requests
            if self.frames_received == 5 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')

    def finish(self):
        """ Executes on termination """
        self.log("Frames Received: {}/{}".format(self.frames_received, self.frames_sent))

    def INGEST(self):
        """ Handle image data received from Pi """
        frame = self.content  # bytes
        self.frames_received += 1
        self.frames_sent = self.header['frames-sent']

        # write current frame to buffer so that it can be sent to a web browser feed
        self.frame_buffer.write(frame)

    def GET(self):
        """ Handle request from web browser """
        self.log("Received Web Browser Request", level='debug')

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
                self.error('Browser Stream Disconnected ({}:{})'.format(ip, port), e)
        else:
            #self.send_error(404)  # couldn't find it
            #self.end_headers()
            self.log("GET request not accounted for", level='debug')
            return
