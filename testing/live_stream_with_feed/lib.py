import io
import socket
import time
from requests import get
import threading


class Base:
    """
    Base class from which all others inherit.
    Implements basic logging functionality
    """
    def __init__(self, debug=False):
        self.debug_mode = debug  # Whether debug mode is active
        self.overlay_msg = ''    # to keep track of the last overlay message
        self.overlay_count = 0   # counter of how many times an output message was overlayed on the same line

        self.exit = False        # Used to exit program and handle errors

    def date(self):
        """ Return the current formatted time """
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        return "{}/{}/{} {}:{}:{} UTC".format(day, month, year, hh, mm, ss)

    def log(self, message, important=False):
        """ Outputs a log message """
        if important:
            print("[{}]".format(message))
        else:
            print("> {}".format(message))

    def debug(self, message, overlay=False):
        """ Sends a debug level message """
        if not self.debug_mode:
            return
        if overlay:  # write an overlayable message
            self.overlay_msg = message
            self.overlay_count += 1  # increment
            beg = ''
            end = '\r'
            count = '[{}]'.format(self.overlay_count)
        else:
            end = '\n'
            count = ''
            self.overlay_msg = ''
            if self.overlay_count > 0:  # stop overlaying
                self.overlay_count = 0  # reset count
                beg = '\n'  # skip a line - don't overlay last message
            else:   # regular message
                beg = ''

        # (debug) [thread_name]: message content [overlay_count]
        print("{}(debug) [{}]: {} {}".format(beg, threading.currentThread().getName(), message, count), end=end)

    def error(self, message, cause=None):
        """ Throw error and signal to disconnect """
        print("[ERROR]: {}".format(message))
        print("[THREAD]: {}".format(threading.currentThread().getName()))
        if cause:
            print("[CAUSE]: {}".format(cause))  # show cause if given
        self.exit = True


class ConnectionBase(Base):
    """
    Object the represents a single connection.
    Holds the socket and associated buffers.
    Runs on it's own thread in the Stream class.
    """
    def __init__(self, ip, port, name, host, debug):
        super().__init__(debug)

        self.server = Address(ip, port)  # address of the server
        self.client = None               # address of client
        self.socket = None     # socket object to read/write to
        self.host = host       # whether this is the server (true) or client (false)

        self.buffer = b''        # incoming stream buffer to read from
        self.header_buffer = []  # outgoing stream buffer

        # variables for each incoming request
        self.method = None   # HTTP request method
        self.path = None     # HTTP request path
        self.version = None  # HTTP request version
        self.header = {}     # header dictionary
        self.content = None  # content received

        self.name = name       # name of connection - usually sent in headers
        self.encoding = 'iso-8859-1'  # encoding for data stream

    def run(self):
        """ Main method to call after instantiation """
        self.setup()  # wait for connection then create socket
        new_thread = threading.Thread(target=self.serve, daemon=True)
        new_thread.start()

    def setup(self):
        """
        Overwritten by server and client connection base classes.
        Initializes socket objects and connections.
        """
        pass

    def start(self):
        """
        Overwritten by connection classes
        Executes on startup after setup() completed
        """
        pass

    def finish(self):
        """
        Overwritten by connection classes
        Executes before connection terminates
        """
        pass

    def serve(self):
        """
        Start all processes on connection.
        """
        try:
            self.start()   # user-defined startup
            while not self.exit:  # run until exit status is set
                self.handle()  # parse and handle all incoming requests
        except KeyboardInterrupt:
            self.log("Manual Termination", True)
        finally:
            self.finish()  # user-defined final execution
            self.close()   # close server

    # The following methods implement reading from the stream
    def handle(self):
        """ Receive, parse, and handle a single request as it is streamed """
        try:
            self.debug("Waiting to receive data...", True)
            data = self.socket.recv(4096)  # receive data from stream (size arbitrary?)
        except BlockingIOError:  # Temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:  # if received data
                self.buffer += data  # append to data buffer
                # TODO: Implement max buffer size? Would need to be well over JPEG image size (~100,000)
            else:  # stream disconnected
                self.log("Peer Disconnected {}".format(self.client if self.host else self.server))
                self.exit = True  # signal to disconnect
                return

        if not self.method:  # request-line not yet received
            self.parse_request_line()
        elif not self.header:  # header not yet received
            self.parse_header()
        elif not self.content:  # content not yet received
            self.parse_content()
        else:  # all parts received
            method_func = getattr(self, self.method)  # get class method that matches name of request method
            method_func()  # call method to handle the request
            self.reset()   # reset all request variables

    def read(self, length, line=False, decode=True):
        """
        If <line> is False:
            - Reads exactly <length> amount from stream.
            - Returns everything including any whitespace
        If <line> is True:
            - Read from stream buffer until CLRF encountered, treating <length> as maximum
            - Returns single line without the trailing CLRF
            - Returns '' if the line received was itself only a CLRF (blank line)
            - Returns None if whole line has not yet been received (buffer not big enough and no CLRF found)
            - if no CLRF before <length> reached, stop reading and throw error
        Decode specifies whether to decode the data from bytes to string. If true, also strips whitespace
        """
        if not line:  # exact length specified
            if len(self.buffer) < length:  # not enough data received to read this amount
                return
            data = self.buffer[:length]
            self.buffer = self.buffer[length:]  # move down the buffer
            if decode:
                data = data.decode(self.encoding)
            return data

        # else, grab a single line, denoted by CLRF
        CLRF = "\r\n".encode(self.encoding)
        loc = self.buffer.find(CLRF)  # find first CLRF
        if loc > length or (loc == -1 and len(self.buffer) > length):  # no CLRF found before max length reached
            self.error("Couldn't read a line from the stream - max length reached (loc:{}, max:{}, length:{})".format(loc, length, len(self.buffer)), self.buffer)
            return
        elif loc == -1:  # CLRF not found, but we may just have not received it yet (max length not reached)
            return

        line = self.buffer[:loc+2]  # slice data including CLRF
        self.buffer = self.buffer[loc+2:]  # move buffer past CLRF
        if decode:
            line = line.decode(self.encoding).strip()  # decode and strip whitespace including CLRF
        return line

    def parse_request_line(self):
        """ Parses the Request-line of an HTTP request, finding the request method, path, and version strings """
        max_len = 256  # max length of request-line before error (arbitrary choice)

        line = self.read(max_len, line=True)  # read first line from stream
        if line is None:  # full line not yet received
            return
        self.debug("Received Request-Line: '{}'".format(line))

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
        max_len = 1024  # max length each header (arbitrary choice)
        for _ in range(max_num):
            line = self.read(max_len, line=True)  # read next line in stream
            if line is None:  # full line not yet received
                return
            if line == '':  # empty line signaling end of headers
                self.debug("All headers received")
                break
            key, val = line.split(':', 1)   # extract field and value by splitting at first colon
            self.header[key] = val.strip()  # remove extra whitespace from value
            self.debug("Received Header '{}':{}".format(key, val))
        else:
            self.error("Too many headers", "> {}".format(max_num))

        if not hasattr(self, self.method):  # if a method for the request doesn't exist
            self.error('Unsupported Request Method', "'{}'".format(self.method))
            return

    def parse_content(self):
        """ Parse request payload, if any """
        length = self.header.get("content-length")
        if length:  # if content length was sent
            content = self.read(int(length), decode=False)  # read raw bytes from stream
            if content:
                self.content = content
                self.debug("Received Content of length: {}".format(len(self.content)))
            else:  # not yet fully received
                return
        else:  # no content length specified - assuming no content sent
            self.content = True  # mark content as 'received'

    def reset(self):
        """ Resets variables associated with a single request """
        self.method = None
        self.path = None
        self.version = None
        self.header = {}
        self.content = None
        self.debug("Reset request variables")

    # The following methods implement writing to the stream
    def add_request(self, method, path='/', version='HTTP/1.1'):
        """ adds a request line to the header buffer. Buffer sent with send_headers() """
        line = "{} {} {}\r\n".format(method, path, version)
        self.debug("Added request line '{}'".format(line))
        self.header_buffer.append(line.encode(self.encoding))

    def add_response(self, code):
        """ Add a response line to the header buffer. Buffer sent with send_headers() """
        version = "HTTP/1.1"
        message = 'MESSAGE'
        response_line = "{} {} {}\r\n".format(version, code, message)

        self.debug("Added response headers with code {}".format(code))
        self.header_buffer.append(response_line.encode(self.encoding))
        self.add_header('Server', 'Streaming Server Python/3.7.3')
        self.add_header('Date', self.date)

    def add_header(self, keyword, value):
        """ add a header to the header buffer. Buffer sent with send_headers() """
        text = "{}: {}\r\n".format(keyword, value)   # text to be sent
        data = text.encode(self.encoding, 'strict')  # convert text to bytes
        self.header_buffer.append(data)              # add to buffer
        self.debug("Added header '{}:{}'".format(keyword, value))
        '''
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False
        '''

    def send_headers(self):
        """ Adds extra headers then a blank line ending the headers buffer, then sends the buffer to the stream """
        self.add_header("name", self.name)
        self.header_buffer.append(b"\r\n")                 # append blank like
        self.socket.sendall(b"".join(self.header_buffer))  # combine all headers and send
        self.header_buffer = []                            # clear header buffer
        self.debug("Sent headers",)

    def send_content(self, content):
        """ Sends content to the stream """
        if type(content) == str:
            data = content.encode(self.encoding)  # encode if string
        elif type(content) == bytes:
            data = content
        else:
            self.error("Cannot send content - format not accounted for.", type(content))
            return
        self.socket.sendall(content)
        self.debug("Sent content of length: {}".format(len(content)))

    def close(self):
        """ Closes the connection """
        self.socket.close()
        self.log("Connection Closed")


class ServerConnectionBase(ConnectionBase):
    """ Create instance to host server on """
    def __init__(self, ip, port, name, debug):
        super().__init__(ip, port, name, True, debug)

    def setup(self):
        """ Create socket and bind to local address then wait for connection from a client """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address
            sock.bind(self.server.tup)  # bind to host address
            self.debug("Socket Bound to {}".format(self.server))
        except Exception as e:
            self.error("Failed to bind socket to {}".format(self.server), e)

        try:  # Listen for connection
            self.debug("Listening for Connection...")
            sock.listen()
        except Exception as e:
            self.error("While listening on {}".format(self.server), e)

        try:  # Accept connection. Accept() returns a new socket object that can send and receive data.
            self.socket, (ip, port) = sock.accept()
            self.client = Address(ip, port)
            self.debug("Accepted Socket Connection From {}".format(self.client))
        except Exception as e:
            self.error("Failed to accept connection from {}".format(self.client))

        self.log("New Connection From: {}".format(self.client))
        # if self.timeout is not None:  # is this needed?
        #    self.socket.settimeout(self.timeout)


class ClientConnectionBase(ConnectionBase):
    """ Create instance to connect to server """
    def __init__(self, ip, port, name, debug):
        super().__init__(ip, port, name, False, debug)

    def setup(self):
        """ Create socket and try to connect to a server ip """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.log("Attempting to connect to {}".format(self.server))
            self.socket.connect(self.server.tup)
            self.log("Socket Connected")
        except Exception as e:
            self.error("Failed to connect to server", e)


class Address:
    """
    Basic class to display ip addresses with port number.
    I got tired of formatting strings.
    """
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        if self.ip in ['', '*', '0.0.0.0']:
            self.ip = ''
        self.rep = '{}:{}'.format(self.ip, self.port)  # string representation
        self.tup = (self.ip, self.port)  # tuple of (ip, port)

    def __repr__(self):
        return self.rep


class FrameBuffer(object):
    """
    Object used as a buffer containing a single frame.
    Can be written to by the picam.
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = threading.Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):  # jpeg image
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # make available to other threads
            self.buffer.seek(0)
        return self.buffer.write(buf)
