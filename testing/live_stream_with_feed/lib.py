import io
import socket
import time
import traceback
import threading
from threading import Thread, Lock, Condition
from requests import get


class Base:
    """
    Base class from which all others inherit.
    Implements global logging functionality.
    """
    debug_mode = False  # Whether debug mode is active.
    last_msg = ''       # to keep track of the last output message
    exit = False        # Used to exit program and handle errors

    def info(self):
        """ prints out startup info """
        if Base.debug_mode:
            print()
            print("---------------------------")
            print(":: RUNNING IN DEBUG MODE ::")
            print("---------------------------")

    def set_debug(self, debug):
        """ Sets the global debug mode """
        Base.debug_mode = debug

    def date(self):
        """ Return the current formatted time """
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        return "{}/{}/{} {}:{}:{} UTC".format(day, month, year, hh, mm, ss)
    
    def display(self, msg):
        """ display a log message """
        if Base.last_msg == msg:  # same message
            return  # Ignore duplicate messages
        Base.last_msg = msg
        print(msg)

    def log(self, message, important=False):
        """ Outputs a log message """
        if important:  # important message just meant to stand out from the rest
            self.display("[{}]".format(message))
        else:  # normal log emssage
            self.display("> {}".format(message))

    def debug(self, msg):
        """ Sends a debug level message """
        if not Base.debug_mode:
            return
        self.display("(debug)[{}]: {}".format(threading.currentThread().getName(), msg))

    def error(self, message, cause=None):
        """ Throw error and signal to disconnect """
        self.display("(ERROR)[{}]: {}".format(threading.currentThread().getName(), message))
        if cause:
            self.display("(CAUSE): {}".format(cause))  # show cause if given
        Base.exit = True

    def traceback(self):
        """ output traceback """
        if Base.debug_mode:
            traceback.print_exc()

    def get_thread_name(self, name):
        """ Given a name, add a unique number to it """
        num = threading.active_count()
        return "Thread[{}]-{}".format(num+1, name)


class Server(Base):
    """
    Handles incoming connections to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """
    def __init__(self, HandlerClass, port, name='Server', debug=False):
        self.HandlerClass = HandlerClass
        self.ip = ''          # ip to bind to
        self.port = port      # port to bind to
        self.name = name      # server name (sent in request headers)
        self.listener = None     # socket that accepts new connections

        self.set_debug(debug)  # set global debug mode
        self.info()

    def create(self):
        """ Create a listening socket object """
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address?
            self.listener.bind((self.ip, self.port))  # bind to host address
            self.debug("Socket Bound to *:{}".format(self.port))
        except Exception as e:
            self.error("Failed to bind socket to *:{}".format(self.port), e)

        try:  # Set as listening connection
            self.debug("Set to listening socket")
            self.listener.listen()
        except Exception as e:
            self.error("Failed to set as listening socket", e)

    def accept(self):
        """ Listen for new connection, then return socket for that connection """
        try:  # Accept() returns a new socket object that can send and receive data.
            self.log("Listening for connections...")
            sock, (ip, port) = self.listener.accept()
            sock.setblocking(False)
            self.log("New Connection From: {}:{}".format(ip, port))
            return sock
        except Exception as e:
            self.error("Failed to accept connection", e)
            return

    def run(self):
        """ Main entry point. Starts each new connections on their own thread """
        self.log("Server IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.create()  # create listener socket
        while not self.exit:
            sock = self.accept()  # wait/accept new connection
            try:
                conn = self.HandlerClass(sock, self)  # create connection with socket
                thread = Thread(target=conn.run, name=self.get_thread_name('Conn'), daemon=True)
                thread.start()  # run connection on new thread
            except Exception as e:
                self.error("Failed to handle request", e)
                sock.close()


class Client(Base):
    """
    Makes a connection to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """
    def __init__(self, HandlerClass, ip, port, name='Client', debug=False):
        self.HandlerClass = HandlerClass
        self.ip = ip         # server ip address to connect to
        self.port = port     # server port to connect through
        self.name = name     # name of client (sent in headers)
        self.socket = None   # socket object

        self.set_debug(debug)  # set global debug mode
        self.info()

    def create(self):
        """ Create socket object and try to connect to server """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.log("Attempting to connect to {}:{}".format(self.ip, self.port))
            self.socket.connect((self.ip, self.port))
            self.log("Socket Connected")
        except Exception as e:
            self.error("Failed to connect to server", e)

        self.socket.setblocking(False)

    def run(self):
        """ Listens for new connections, then starts them on their own thread """
        self.log("Client IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.create()
        if not self.exit:
            conn = self.HandlerClass(self.socket, self)  # create new connection for the client
            conn.run()  # Only one connection, so no need to thread


class Handler(Base):
    """
    Object that represents a single connection between server and client
    Handles incoming requests on a single socket.
    Holds the socket and associated buffers
    Holds a reference to whatever created it (Server or Client). Used to share data between connections
    """
    def __init__(self, sock, parent):
        self.socket = sock       # socket object to read/write to
        self.parent = parent     # object that created this connection (either the Server or Client)
        self.peer = None         # address of machine on other end of connection

        self.in_buffer = b''      # incoming stream buffer to read from
        self.out_buffer = b''     # outgoing stream buffer to write to
        self.write_lock = Lock()  # lock for out_buffer

        self.request = Request()  # current request being parsed

        self.name = parent.name   # name of connection - usually sent in headers
        self.encoding = 'iso-8859-1'  # encoding for data stream (latin-1)

    def run(self):
        """ Main entry point - called by parent """
        try:
            self.peer = self.socket.getpeername()
            self.start()  # user-defined startup function
            while not self.exit:   # run until exit status is set
                self.pull()        # Attempt to fill in_buffer from stream
                if not self.exit:
                    self.handle()  # parse and handle any incoming requests
                if not self.exit:
                    self.push()    # Attempt to push out_buffer to stream
        except KeyboardInterrupt:
            self.log("Manual Termination", True)
        except (ConnectionResetError, BrokenPipeError):
            self.log("Peer Disconnected ({}:{})".format(*self.peer), True)
        except Exception as e:  # any other error
            self.traceback()
            self.error(e)
        finally:
            self.finish()  # user-defined final execution
            self.close()   # close server

    def start(self):
        """
        Temporary until user interface is created
        Executes when the connection is established
        Overwritten by user
        """
        # TODO: Remove this when a manual user interface is created
        pass

    def finish(self):
        """
        Temporary until user interface is created
        Executes before connection terminates
        Overwritten by user
        """
        # TODO: Remove this when a manual user interface is created
        pass

    def pull(self):
        """ Receive raw bytes from the socket stream and adds to the in_buffer """
        try:
            data = self.socket.recv(4096)  # Receive data from stream
        except BlockingIOError:  # catch no data on non-blocking socket
            pass
        else:
            if data:  # received data
                self.debug("Pulled data from stream {}".format(len(data)))
                self.in_buffer += data  # append data to incoming buffer
            else:  # stream disconnected
                raise BrokenPipeError

    def push(self):
        """ Attempts to send the out_buffer to the stream """
        if self.out_buffer == b'':  # nothing to write
            return
        try:
            with self.write_lock:  # get lock
                sent = self.socket.send(self.out_buffer)  # try to send as much data from the out_buffer
                self.out_buffer = self.out_buffer[sent:]  # move down buffer according to how much data was sent
                self.debug("Pushed buffer to stream")
        except BlockingIOError:  # no response when non-blocking socket used
            pass

    def handle(self):
        """ Parse and handle a single request from the buffers """
        if not self.request.request_received:  # request-line not yet received
            self.parse_request_line()
        elif not self.request.header_received:  # header not yet fully received
            self.parse_header()
        elif not self.request.content_received:  # content not yet received
            self.parse_content()  # may or may not have content
        else:   # full request has been received
            method_func = getattr(self, self.request.method)  # get handler method that matches name of request method
            method_thread = threading.Thread(target=method_func, args=(self.request,),  name=self.get_thread_name(method_func.__name__), daemon=True)
            method_thread.start()  # call method in new thread to handle the request
            self.reset()   # reset all request variables

    def read(self, length, line=False, decode=True):
        """
        Read and return data from the incoming buffer. Return None if not available.
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
        if self.in_buffer == b'':  # nothing to read
            return
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

    def send(self, response):
        """ Compiles the response object then adds it to the out_buffer """
        data = response.get_data()
        if not data:  # error which has been caught, hopefully
            return
        self.send_raw(data)

    def send_raw(self, data):
        """ Sends raw bytes data as-is to the out_buffer """
        with self.write_lock:  # get lock
            self.out_buffer += data  # add data to buffer
            self.debug("Added data to outgoing buffer")

    def parse_request_line(self):
        """ Parses the Request-line of a request, finding the request method, path, and version strings. """
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

        self.request.method = words[0]
        self.request.path = words[1]
        self.request.version = words[2]
        self.request.request_received = True   # mark request-line as received

        if not hasattr(self, self.request.method):  # if a method for the request doesn't exist
            self.error('Unsupported Request Method', "'{}'".format(self.request.method))

    def parse_header(self):
        """ Fills the header dictionary from the received header text. """
        max_num = 32    # max number of headers (arbitrary choice)
        max_len = 1024  # max length each header (arbitrary choice)
        for _ in range(max_num):
            line = self.read(max_len, line=True)  # read next line in stream
            self.debug("Read Header '{}'".format(line))
            if line is None:  # full line not yet received
                return
            if line == '':  # empty line signaling end of headers
                self.debug("All headers received")
                self.request.header_received = True  # mark header as received
                break
            key, val = line.split(':', 1)   # extract field and value by splitting at first colon
            self.request.header[key] = val.strip()  # remove extra whitespace from value
        else:
            self.error("Too many headers", "> {}".format(max_num))
            return

    def parse_content(self):
        """ Parse request payload, if any. """
        length = self.request.header.get("content-length")
        if length:  # if content length was sent
            content = self.read(int(length), decode=False)  # read raw bytes from stream
            if content:
                self.request.content = content
                self.debug("Received Content of length: {}".format(len(self.request.content)))
                self.request.content_received = True  # mark content as received
            else:  # not yet fully received
                return
        else:  # no content length specified - assuming no content sent
            self.request.content_received = True  # mark content as received
            return  # TODO: Is there a better way to determine for sure whether a request has only a header?

    def reset(self):
        """ Get ready for a new request and push the current one onto the request buffer """
        self.request = Request()
        self.debug("Reset request packet")

    def close(self):
        """ Closes the connection """
        self.socket.close()
        self.log("Connection Closed\n")

    # extra helpful stuff
    def send_multipart(self, buffer, content_type, boundary):
        """
        Continually creates and sends multipart-type responses to the stream.
        Used to send an image stream to a browser.
        <Buffer> is a buffer with a read() method and a threading condition to read data from
        <content-type> will be put into a content-type header.
        <boundary> us the separator between "packets"
        """
        res = Request()
        res.add_response(200)
        res.add_header('Age', 0)
        res.add_header('Cache-Control', 'no-cache, private')
        res.add_header('Pragma', 'no-cache')
        res.add_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.send(res)

        # occurs before every main payload
        header = '--{}\r\n'.format(boundary).encode(self.encoding)
        header += 'Content-Type: {}\r\n\r\n'.format(content_type).encode(self.encoding)  # single header with a blank line after
        try:
            self.debug("Started multipart stream")
            while True:
                with buffer.condition:
                    buffer.condition.wait()
                    data = buffer.read()
                packet = header + data + b'\r\n'
                self.send_raw(packet)
        except Exception as e:
            self.error('Browser Stream Disconnected ({}:{})'.format(*self.peer), e)


class Request(Base):
    """
    Holds all data from one request.
    Used by Handler class to store incoming/outgoing requests.
    To use, call the appropriate add_ methods to add parts of the HTTP request,
        then pass the object to self.send (self referring to the Handler class the request is used in)
    """
    def __init__(self):
        self.encoding = 'iso-8859-1'    # byte encoding
        # TODO: make encoding not hard-coded? It's defined again in the Handler class. Maybe there's a nice way to pass it down? putting it in the constructor would not be ideal because the user has to call it in custom request methods.

        self.method = None      # request method (GET, POST, etc..)
        self.path = None        # request path
        self.version = None     # request version (HTTP/X.X)
        self.header = {}        # dictionary of headers
        self.content = b''      # request content in bytes

        self.request_received = False  # whether the whole request line has been received
        self.header_received = False   # whether all headers have been received
        self.content_received = False  # whether all content has been received

        self.code = None     # HTTP response code
        self.message = None  # Response message

    def add_request(self, method, path='/', version='HTTP/1.1'):
        """ Add request method, path, and version """
        self.method = method
        self.path = path
        self.version = version

    def add_response(self, code):
        """ Add a response code, message, version, and default headers. Used to respond to web browsers. """
        self.code = code
        self.version = "HTTP/1.1"
        if code == 200:
            self.message = 'OK'
        elif code == 301:
            self.message = "Moved Permanently"
        elif code == 404:
            self.message = 'Not Found'
        else:
            self.message = "MESSAGE"

        self.add_header('Server', 'Streaming Server Python/3.7.3')  # TODO: make this not hard coded (Not really necessary yet)
        self.add_header('Date', self.date())

    def add_header(self, keyword, value):
        """ Add a single header line """
        self.header[keyword] = value

    def add_content(self, content):
        """ Add main content payload """
        if type(content) == str:
            data = content.encode(self.encoding)  # encode if string
        elif type(content) == bytes:
            data = content
        else:  # type conversion not implemented
            self.error("Cannot send content - type not accounted for.", type(content))
            return
        self.content = data

    def verify(self):
        """ Verify that this object meets all requirements and can be safely sent to the stream """
        if self.method and self.code:  # trying to send both a response and a request
            self.error("Cannot send both a response and a request", 'You added request method "{}" and response code "{}"'.format(self.method, self.code))
            return False
        if not self.method and not self.code and self.header:
            self.error("If you send a header, you must include a request or response as well")
            return False
        return True

    def get_data(self):
        """ Formats all data into an encoded HTTP request and returns it """
        if not self.verify():
            return
        data = b''  # data to be returned

        # first line
        if self.method:
            request_line = "{} {} {}\r\n".format(self.method, self.path, self.version)
            data += request_line.encode(self.encoding)
            self.debug("Added request line '{}'".format(request_line.strip()))

        if self.code:
            response_line = "{} {} {}\r\n".format(self.version, self.code, self.message)
            data += response_line.encode(self.encoding)
            self.debug("Added response line '{}'".format(response_line))

        # headers
        for key, value in self.header.items():
            header = "{}: {}\r\n".format(key, value)
            data += header.encode(self.encoding)
            self.debug("Added header '{}:{}'".format(key, value))
        if self.header:
            data += b'\r\n'  # add a blank line to denote end of headers
            self.debug("Ended headers")

        # content
        if self.content:
            data += self.content  # content should already be in bytes
            self.debug("Added content of length: {}".format(len(self.content)))

        return data


# TODO: Is this the only place that custom buffer classes can go so both collection_lib and ingestion_lib can acces them? I'd rather they be in the same file as the c
class FrameBuffer(object):
    """
    A thread-safe buffer to store frames in
    The write() method can be used by a Picam
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):  # jpeg image
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # wake any waiting threads
            self.buffer.seek(0)
        return self.buffer.write(buf)