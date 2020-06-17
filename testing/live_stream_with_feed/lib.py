import sys


class StreamBase:
    """
    Base class for both Server and Client classes.
    Provides the ability to send and read HTTP requests.
    After initialization, call server() to start the server
    Methods that are overwritten in Server and Client classes:
        - setup(): initializes socket connection
        - stream(): continually performs read/write action to TCP stream
        - finish(): executes before termination of connection
    """
    def __init__(self, ip, port, debug=False):
        self.ip = ip         # ip to bind/connect socket to
        self.port = port     # server port

        self.pi_ip = None    # RasPi ip
        self.pi_port = None  # RasPi port

        self.socket = None       # socket object
        self.buffer = b''        # incoming stream buffer to read from
        self.header_buffer = []  # outgoing header buffer

        # variables for each request
        self.method = None       # HTTP request method
        self.path = None         # HTTP request path
        self.version = None      # HTTP request version
        self.header = {}         # incoming header dictionary
        self.content = None      # content received

        # misc.
        self.frames_sent = 0      # number of frames sent to server (Sent in header)
        self.frames_received = 0  # number of frames received by server

        self.exit = False             # flag to signal clean termination
        self.encoding = 'iso-8859-1'  # encoding for data stream
        self.debug = debug            # specifies debug mode

    def serve(self):
        """ Start the server """
        self.setup()  # initialize socket object and connect
        try:
            self.stream()  # main streaming loop
        finally:
            self.finish()  # final executions
            self.close()   # close server

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
        """ Receive, parse, and handle a single request as it is streamed """
        try:
            data = self.socket.recv(4096)  # receive data from pi (size arbitrary?)
        except BlockingIOError:  # Temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:  # if received data
                self.buffer += data  # append to data buffer
                # TODO: Implement max buffer size? Will need to be well over JPEG image size (~100,000)
            else:  # stream disconnected
                self.log("Client Disconnected {}:{}".format(self.pi_ip, self.pi_port))
                self.exit = True  # signal to disconnect
                return

        if not self.method:  # request-line not yet received
            self.parse_request_line()
        elif not self.header:  # header not yet received
            self.parse_header()
        elif not self.content:  # content not yet received
            self.parse_content()
        else:  # all parts received
            if not hasattr(self, self.method):  # if a method for the request doesn't exist
                self.error('Unsupported Method', self.method)
                return
            method_func = getattr(self, self.method)  # get class method that matches name of request method
            method_func()  # call it to handle the request
            self.reset()  # reset all request variables

    def read(self, length, line=False):
        """
        If line is False:
            - Reads exactly <length> amount from stream.
            - Returns everything including any whitespace
        If line is True:
            - Read from stream buffer until CLRF encountered
            - Returns single decoded line without the trailing CLRF
            - Returns '' if the line received was itself only a CLRF (blank line)
            - Returns None if whole line has not yet been received (buffer not at <length> yet)
            - if no CLRF before <length> reached, stop reading and throw error
        """
        if not line:  # exact length specified
            if len(self.buffer) < length:  # not enough data received to read this amount
                return
            data = self.buffer[:length].decode(self.encoding)  # slice exact amount
            self.buffer = self.buffer[length:]  # move down the buffer
            return data

        # else, grab a single line, denoted by CLRF
        CLRF = "\r\n".encode(self.encoding)
        loc = self.buffer.find(CLRF)  # find first CLRF
        if loc > length or (loc == -1 and len(self.buffer) > length):  # no CLRF found before max length reached
            self.error("buffer too long before CLRF (max length: {})".format(length), self.buffer.decode(self.encoding))
            return
        elif loc == -1:  # CLRF not found, but we may just have not received it yet.
            return

        line = self.buffer[:loc+2]  # slice including CLRF
        self.buffer = self.buffer[loc+2:]  # move buffer past CLRF
        return line.decode(self.encoding).strip()  # decode and strip whitespace including CLRF

    def parse_request_line(self):
        """ Parses the Request-line of an HTTP request, finding the request method, path, and version strings """
        max_len = 1024  # max length of request-line before error (arbitrary choice)

        line = self.read(max_len, line=True)  # read first line from stream
        if line is None:  # nothing yet
            return
        self.log("Received Request-Line: '{}'".format(line), level='debug')

        words = line.split()
        if len(words) != 3:
            err = "Request-Line must conform to HTTP Standard (METHOD /path HTTP/X.X\\r\\n)"
            self.error(err, line)
            return

        self.method = words[0]
        self.path = words[1]
        self.version = words[2]

    def parse_header(self):
        """ Fills the header dictionary from the received header text """
        max_num = 32    # max number of headers (arbitrary choice)
        max_len = 1024  # max length of headers (arbitrary choice)
        for _ in range(max_num):
            line = self.read(max_len, line=True)  # read next line in stream
            if line is None:  # nothing yet
                return
            if line == '':  # empty line signaling end of headers
                self.log("All headers received", level='debug')
                break
            key, val = line.split(':', 1)  # extract field and value by splitting at first colon
            self.header[key] = val.strip()  # remove extra whitespace from value
            self.log("Received Header '{}':{}".format(key, val), level='debug')
        else:
            self.error("Too many headers", "> {}".format(max_num))

    def parse_content(self):
        """ Parse request payload, if any """
        length = self.header.get("content-length")
        if length:  # if content length was sent
            content = self.read(int(length))
            if content:
                self.content = content
                self.log("Received Content of length: {}".format(len(self.content)), level='debug')
            else:  # not yet fully received
                return
        # TODO: What if request has a payload without a specified length?

    def reset(self):
        """ Resets variables associated with a single request """
        self.method = None
        self.path = None
        self.version = None
        self.header = {}
        self.content = None
        self.log("Reset request variables", level='debug')

    def send_request_line(self, method, path='/', version='HTTP/1.1'):
        """ sends an HTTP request line to the stream """
        line = "{} {} {}\r\n".format(method, path, version)
        self.socket.sendall(line.encode(self.encoding))

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
        self.socket.sendall(b"".join(self.header_buffer))  # combine all headers and send
        self.header_buffer = []                         # clear header buffer

    def send_content(self, content):
        """ Sends content to the stream """
        if type(content) == str:
            data = content.encode(self.encoding)
        elif type(content) == bytes:
            data = content
        else:
            self.error("Content format not accounted for", type(content))
            return
        self.socket.sendall(content)

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
            print("[ERROR]: {}".format(message))
            if cause:
                print("[CAUSE]: {}".format(cause))
        elif level == 'debug' and self.debug:  # only show in debug mode
            print("[debug]: {}".format(message))

    def error(self, message, cause=None):
        """ Throw error and signal to disconnect"""
        self.log(message, cause=cause, level='error')
        self.exit = True
