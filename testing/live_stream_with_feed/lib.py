import io
import sys
import socket
import picamera
from threading import Condition
from requests import get
from time import sleep, strftime


class StreamBase:
    def __init__(self, ip, port, debug=False):
        self.ip = ip         # ip to bind/connect socket to
        self.port = port     # server port

        self.pi_ip = None    # RasPi ip
        self.pi_port = None  # RasPi port

        self.socket = None   # socket object
        self.rfile = None    # incoming file object to read from
        self.wfile = None    # outgoing file object to write to

        self.header_buffer = []  # outgoing header buffer

        # variables for each request
        self.method = None       # HTTP request method
        self.path = None         # HTTP request path
        self.version = None      # HTTP request version
        self.header = None       # incoming header dictionary
        self.content = None      # content received

        # misc.
        self.frames_sent = 0      # number of frames sent to server (Sent in header)
        self.frames_received = 0  # number of frames received by server

        self.exit = False             # flag to signal clean termination
        self.encoding = 'iso-8859-1'  # encoding for data stream
        self.debug = debug            # specifies debug mode

        # funcs
        self.serve()

    def serve(self):
        """ Start the server """
        self.setup()  # initialize socket object and connect

        # Create read/write file stream objects from socket
        self.rfile = self.socket.makefile('rb')
        self.wfile = self.socket.makefile('wb')

        try:
            self.stream()
        finally:
            self.finish()
            self.close()

    def setup(self):
        """
        Overwritten in Server and Client classes to create the socket object.
        """
        pass

    def stream(self):
        """
        Overwritten by Server and Client classes.
        Main method called after class instance creation.
        Continually reads/writes to file streams.
        Calls handle_request() in a loop.
        """
        pass

    def finish(self):
        """
        Overwritten in Server and Client classes.
        Execute any last processes before termination
        """
        pass

    def handle(self):
        """ Parse and handle a single request as it is streamed """
        if not self.method:  # request-line not yet received
            self.parse_request_line()
        elif not self.header:  # header not yet received
            self.parse_header()
        elif not self.content:  # content not yet received
            self.parse_content()
            if not hasattr(self, self.method):  # if a method for the request doesn't exist
                self.error('Unsupported Method', self.method)

            method_func = getattr(self, self.method)  # get class method that matches name of request method
            method_func()  # call it to handle the request
            self.reset()  # reset all request variables

    def parse_request_line(self):
        """ Parses the Request-line of an HTTP request, finding the request method, path, and version strings """
        max_len = 1024  # max length of request-line before error (arbitrary choice)

        raw_line = self.rfile.readline(max_len+1)  # read raw byte stream first line
        if not raw_line:  # nothing yet
            return
        if len(raw_line) > max_len:  # too long
            self.error("Request-Line too long", "Length: {}".format(len(raw_line)))

        line = str(raw_line, self.encoding)  # decode raw
        words = line.split()
        if len(words) != 3:
            err = "Request-Line must conform to HTTP Standard (METHOD /path HTTP/X.X\\r\\n)"
            self.error(err, line)

        self.method = words[0]
        self.path = words[1]
        self.version = words[2]

    def parse_header(self):
        """ Fills the header dictionary from the received header text """
        max_num = 32    # max number of headers (arbitrary choice)
        max_len = 1024  # max length of headers (arbitrary choice)
        for _ in range(max_num):
            raw_line = self.rfile.readline(max_len+1)  # read next line in stream
            if not raw_line:  # nothing yet
                return
            if len(raw_line) > max_len:  # too long
                self.error("Header too long", "Length: {}".format(len(raw_line)))

            line = str(raw_line, 'iso-8859-1')  # decode raw
            if line == '\r\n':  # empty line signaling end of headers
                break
            key, val = line.split(':', 1)  # extract field and value by splitting at first colon
            self.header[key] = val.strip()  # remove extra whitespace from value
        else:
            self.error("Too many headers", ">= {}".format(max_num))

    def parse_content(self):
        """ Parse request payload, if any """
        length = self.header.get("content-length")
        if length:  # if content length was sent
            data = self.rfile.read(length)
            self.content = data.decode(self.encoding)
        # TODO: What if request has a payload without a specified length?

    def reset(self):
        """ Resets variables associated with a single request """
        self.method = None
        self.path = None
        self.version = None
        self.header = None
        self.content = None
        self.log("Reset request variables", level='debug')

    def add_header(self, keyword, value):
        """ add a MIME header to the headers buffer. Does not send to stream. """
        text = "{}: {}\r\n".format(keyword, value)   # text to be sent
        data = text.encode(self.encoding, 'strict')  # convert text to bytes
        self.header_buffer.append(data)              # add to buffer
        '''
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False
        '''

    def send_headers(self):
        """ Adds a blank line ending the MIME headers, then sends the header buffer to the stream """
        self.header_buffer.append(b"\r\n")              # append blank like
        self.wfile.write(b"".join(self.header_buffer))  # combine all headers and send
        self.header_buffer = []                         # clear header buffer
        self.wfile.flush()

    def send_content(self, content):
        """ Sends content to the stream """
        if type(content) == str:
            data = content.encode(self.encoding)
        elif type(content) == bytes:
            data = content
        else:
            self.error("Content format not accounted for", type(content))
        self.wfile.write(content)
        self.wfile.flush()

    def close(self):
        """ Closes the connection """
        self.socket.close()
        self.log("Connection Closed")

    def log(self, message, cause=None, level='log'):
        """ Outputs a message according to debug level """
        if level == 'log':  # always show message
            print("> {}".format(message))
        elif level == 'status':  # always show as important message
            print("[{}]".format(message))
        elif level == 'error':  # always show as error
            print("[ERROR]: {}")
            if cause:
                print("[CAUSE]: {}".format(cause))
        elif level == 'debug' and self.debug:  # only show in debug mode
            print("[debug]: {}".format(message))

    def error(self, message, cause=None):
        """ Throw error and halt """
        self.log(message, cause)
        sys.exit()


class StreamServer(StreamBase):
    def __init__(self, port, debug=False):
        super().__init__('', port, debug)  # accept any ip on this port

    def setup(self):
        """ Create socket and bind to local address then wait for connection from client """
        self.log("IP:", get('http://ipinfo.io/ip').text.strip())  # show this machine's public ip

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        self.log("Socket Created")

        try:  # Bind socket to ip and port
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address
            sock.bind((self.ip, self.port))  # accept any ip on this port
            self.log("Socket Bound")
        except Exception as e:
            self.error("Failed to bind socket to {}:{}".format(self.ip, self.port), e)

        try:  # Listen for connection
            self.log("Listening for Connection on {}:{}".format(self.ip, self.port))
            sock.listen()
        except Exception as e:
            self.error("Error while listening on {}:{}".format(self.ip, self.port), e)

        try:  # Accept connection. Accept() returns a new socket object that can send and receive data.
            self.socket, (self.pi_ip, self.pi_port) = sock.accept()
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
            if self.frames_received == 1 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')

    def finish(self):
        """ Executes on termination """
        self.log("Frames Received: {}/{}".format(self.frames_received, self.frames_sent))

    def INGEST(self):
        """ Handle image data received from Pi """
        frame = self.content
        self.frames_received += 1
        self.frames_sent = self.header['frames-sent']

    def GET(self):
        """ Handle request from web browser """


class StreamClient(StreamBase):
    def __init__(self, ip, port, resolution='640x480', framerate=24, debug=False):
        super().__init__(ip, port, debug)

        self.camera = None              # picam object
        self.resolution = resolution    # resolution of stream
        self.framerate = framerate      # camera framerate
        self.output = None              # file-like object buffer for the camera to stream to

    def setup(self):
        """ Create socket and connect to server ip """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        self.log("Socket Created")

        try:  # connect socket to given address
            self.log("Attempting to connect to {}:{}".format(self.ip, self.port))
            self.socket.connect((self.ip, self.port))
            self.log("Socket Connected")
        except Exception as e:
            self.error("Failed to connect to server", e)

    def stream(self):
        self.start_recording()
        msg = False  # flag for displaying the streaming notification
        while not self.exit:  # run until exit status is set
            self.send_images()
            if self.frames_sent == 1 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')

    def send_images(self):
        """ Handle sending images to the stream """
        with self.output.condition:
            self.output.condition.wait()
            frame = self.output.frame  # get next frame from picam

        self.frames_sent += 1
        self.add_header("content-length", len(frame))
        self.add_header("frames-sent", self.frames_sent)
        self.send_headers()
        self.send_content(frame)

    def finish(self):
        """ Executes on termination """
        self.stop_recording()  # stop recording

    def start_recording(self):
        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.output = StreamOutput()  # file-like output object for the picamera to write to
        self.camera.start_recording(self.output, format='mjpeg')
        self.log("Started Recording: {}".format(strftime('%Y/%m/%d %H:%M:%S')))
        sleep(2)

    def stop_recording(self):
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(strftime('%Y/%m/%d %H:%M:%S')))


class StreamOutput(object):
    """
    Used by Picam's start_recording() method.
    Writes frames to a buffer to be sent to the client
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # notify all clients that it's available
            self.buffer.seek(0)
        return self.buffer.write(buf)
