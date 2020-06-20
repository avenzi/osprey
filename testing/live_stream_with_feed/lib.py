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

        self.in_buffer = b''     # incoming stream buffer to read from
        self.out_buffer = b''    # outgoing stream buffer to write to

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
        new_thread.start()  # call main service loop on new thread

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
        """ Main loop - Start all processes on connection """
        try:
            self.start()        # user-defined startup function
            while not self.exit:  # run until exit status is set
                self.pull()    # fill in_buffer from stream
                self.handle()  # parse and handle any incoming requests
                self.push()    # send out_buffer to stream
        except KeyboardInterrupt:
            self.log("Manual Termination", True)
        except ConnectionResetError:
            self.log("Peer Disconnected", True)
        except BrokenPipeError:
            self.log("Peer Disconnected", True)
        finally:
            self.finish()  # user-defined final execution
            self.close()   # close server

    def pull(self):
        """ Receive raw bytes from the stream and adds to the in_buffer """
        try:
            data = self.socket.recv(4096)  # Receive data from stream
        except BlockingIOError:  # catch no data on non-blocking socket
            pass
        else:
            if data:  # received data
                self.in_buffer += data  # append data to incoming buffer
            else:  # stream disconnected
                self.log("Peer Disconnected (is this error showing?) {}".format(self.client if self.host else self.server))
                self.exit = True
                # TODO: not sure whether I should try to put this errot in the main loop with the others. It's not an exception, though

    def push(self):
        """ Attempts to send the out_buffer to the stream """
        try:
            self.socket.sendall(self.out_buffer)
        except BlockingIOError:  # no response when non-blocking socket used
            pass

    def handle(self):
        """ Parse and handle a single request from the buffers """
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
        Read data from the incoming buffer
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
            if len(self.in_buffer) < length:  # not enough data received to read this amount
                return
            data = self.in_buffer[:length]
            self.in_buffer = self.in_buffer[length:]  # move down the buffer
            if decode:
                data = data.decode(self.encoding)
            return data

        # else, grab a single line, denoted by CLRF
        CLRF = "\r\n".encode(self.encoding)
        loc = self.in_buffer.find(CLRF)  # find first CLRF
        if loc > length or (loc == -1 and len(self.in_buffer) > length):  # no CLRF found before max length reached
            self.error("Couldn't read a line from the stream - max length reached (loc:{}, max:{}, length:{})".format(loc, length, len(self.in_buffer)), self.in_buffer)
            return
        elif loc == -1:  # CLRF not found, but we may just have not received it yet (max length not reached)
            return

        line = self.in_buffer[:loc+2]  # slice data including CLRF
        self.in_buffer = self.in_buffer[loc+2:]  # move buffer past CLRF
        if decode:
            line = line.decode(self.encoding).strip()  # decode and strip whitespace including CLRF
        return line

    def parse_request_line(self):
        """ Parses the Request-line of a request, finding the request method, path, and version strings """
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

    def add_request(self, method, path='/', version='HTTP/1.1'):
        """ Add a standard HTTP request line to the outgoing buffer """
        line = "{} {} {}\r\n".format(method, path, version)
        self.out_buffer += line.encode(self.encoding)
        self.debug("Added request line '{}'".format(line))

    def add_response(self, code):
        """ Add a response line to the header buffer. Used to respond to web browsers. """
        version = "HTTP/1.1"
        message = 'MESSAGE'  # TODO: make this dynamic according to the code sent (not really that necessary yet)
        response_line = "{} {} {}\r\n".format(version, code, message)  # text to be sent

        self.debug("Added response with code {}".format(code))
        self.out_buffer += response_line.encode(self.encoding)  # convert to bytes and add to buffer
        self.add_header('Server', 'Streaming Server Python/3.7.3')
        self.add_header('Date', self.date)

    def add_header(self, keyword, value):
        """ Add a standard HTTP header to the outgoing buffer """
        text = "{}: {}\r\n".format(keyword, value)      # text to be sent
        self.out_buffer += text.encode(self.encoding)   # convert to bytes and add to buffer
        self.debug("Added header '{}:{}'".format(keyword, value))

        # this bit may be necessary at some point in the future
        '''
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.exit = True
            elif value.lower() == 'keep-alive':
                ?????
        '''

    def end_headers(self):
        """ Adds any extra headers then a blank line ending the header section """
        self.add_header("name", self.name)  # name of this client
        self.out_buffer += b'\r\n'          # blank like
        self.debug("Ended headers")

    def add_content(self, content):
        """ Add content to the buffer AFTER all end_headers() has been called """
        if type(content) == str:
            data = content.encode(self.encoding)  # encode if string
        elif type(content) == bytes:
            data = content
        else:  # type conversion not implemented
            self.error("Cannot send content - type not accounted for.", type(content))
            return
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

        #self.socket.setblocking(False)


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
