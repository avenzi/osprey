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
    debug_level = 0     # debugging level
    last_msg = ''       # to keep track of the last output message
    exit = False        # Used to exit program and handle errors
    print_lock = Lock()  # lock on output

    def info(self):
        """ prints out startup info """
        if Base.debug_level:
            print()
            print("------------------------------")
            print(":: RUNNING IN DEBUG MODE {} ::".format(Base.debug_level))
            print("------------------------------")

    def set_debug(self, debug):
        """ Sets the global debug mode """
        Base.debug_level = debug

    def date(self):
        """ Return the current time in HTTP Date-header format """
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    
    def display(self, msg):
        """ display a log message """
        if Base.last_msg == msg:  # same message
            return  # Ignore duplicate messages
        with Base.print_lock:
            Base.last_msg = msg
            print(msg)

    def log(self, message, important=False):
        """ Outputs a log message """
        if important:  # important message just meant to stand out from the rest
            self.display("[{}]".format(message))
        else:  # normal log emssage
            self.display("> {}".format(message))

    def debug(self, msg, level=1):
        """ Sends a debug level message """
        if Base.debug_level >= level:
            self.display("(debug)[{}]: {}".format(threading.currentThread().getName(), msg))

    def error(self, message, cause=None):
        """ Throw error and signal to disconnect """
        self.display("(ERROR)[{}]: {}".format(threading.currentThread().getName(), message))
        if cause is not None:
            self.display("(CAUSE): {}".format(cause))  # show cause if given
        Base.exit = True

    def traceback(self):
        """ output traceback """
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
        self.listener = None  # socket that accepts new connections

        self.connections = {}  # index of all connections to the server. (full:address, Handler Object)

        self.set_debug(debug)  # set global debug mode
        self.info()

    def create(self):
        """ Create a listening socket object """
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            # self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address?
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
            sock, (ip, port) = self.listener.accept()
            sock.setblocking(False)
            self.log("New Connection From: {}:{}".format(ip, port))
            return sock
        except KeyboardInterrupt:
            self.error("Manual Termination")
            return
        except Exception as e:
            self.error("Failed to accept connection", e)
            return

    def run(self):
        """ Main entry point. Starts each new connections on their own thread """
        self.log("Server IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.create()  # create listener socket
        self.log("Listening for connections...")
        while not self.exit:
            sock = self.accept()  # wait/accept new connection
            if self.exit:
                return
            try:
                conn = self.HandlerClass(sock, self)  # create connection with socket
                address = "{}:{}".format(*sock.getpeername())
                self.connections[address] = conn
                thread = Thread(target=conn.run, name=self.get_thread_name('Conn'), daemon=True)
                thread.start()  # run connection on new thread
            except Exception as e:
                self.error("Failed to handle request", e)
                sock.close()

    def main_page(self):
        """ Returns the HTML for the main selection page """
        page = """
        <html>
        <head><title>Main Page</title></head>
        <body><h1>MainPage</h1>
        """
        for address, conn in self.connections.items():
            if not conn.name:  # if name is not specified, this is a browser connection, not a data streaming connection
                continue
            page += "<a href='/{}'>{} ({})</a>\n".format(address, conn.name, address)
        page += "</body></html>"
        return page

    def stream_page(self, ID):
        """ Creates a streaming page """
        conn = self.connections[ID]
        aspect = conn.resolution[0]/conn.resolution[1]
        # TODO: Force the size of the image to be constant while keeping the original aspect ratio.
        page = """
        <html>
        <head><title>{name}</title></head>
        <body>
            <h1>{name}</h1>
            <img src="stream.mjpg" width="{width}" height="{height}" />
            <a href='/index'>Back</a>
        </body>
        </html>
        """.format(name=conn.name, width=conn.resolution[0], height=conn.resolution[1])
        return page


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
            conn.run()   # Only one connection, so no need to thread


class HandlerBase(Base):
    """
    Inherited by ServerHandler and ClientHandler.
    Object that represents a single connection between server and client.
    Handles incoming requests on a single socket.
    Holds the socket and associated buffers.
    """
    def __init__(self, sock):
        self.socket = sock       # socket object to read/write to
        self.peer = None         # address of machine on other end of connection

        self.in_buffer = b''      # incoming stream buffer to read from
        self.out_buffer = b''     # outgoing stream buffer to write to
        self.write_lock = Lock()  # lock for out_buffer
        self.request = Request()  # current request being parsed
        self.encoding = 'iso-8859-1'  # encoding for data stream (latin-1)

        # Information sent/received in INIT
        self.name = None              # Name to identify connection. Sent by 'name' header in INIT
        self.framerate = None         # Frame rate of stream, if any. Can be specified by the 'framerate' header in INIT
        self.resolution = (640, 480)  # Default resolution of images. Can be changed by the 'resolution' header in INIT

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
        except (ConnectionResetError, BrokenPipeError) as e:
            self.log("Peer Disconnected ({}:{})".format(*self.peer), True)
            self.debug("Disconnection was due to: {}".format(e))
        except Exception as e:  # any other error
            self.traceback()
            self.error(e)
        finally:
            self.finish()  # user-defined final execution
            self.close()   # close server

    def start(self):
        """
        Executes when the connection is established
        Overwritten by user
        """
        pass

    def finish(self):
        """
        Executes before connection terminates
        Overwritten by user
        """
        pass

    def pull(self):
        """ Receive raw bytes from the socket stream and adds to the in_buffer """
        try:
            data = self.socket.recv(4096)  # Receive data from stream
        except BlockingIOError:  # catch no data on non-blocking socket
            pass
        else:
            if data:  # received data
                self.debug("Pulled data from stream", 3)
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
                self.debug("Pushed buffer to stream: {}".format(sent), 3)
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
            self.request = Request()  # ready for new request

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

    def parse_request_line(self):
        """ Parses the Request-line of a request, finding the request method, path, and version strings. """
        max_len = 256  # max length of request-line before error (arbitrary choice)

        line = self.read(max_len, line=True)  # read first line from stream
        if line is None:  # full line not yet received
            return
        if line == '':  # blank line
            return   # skip
        self.debug("Received Request-Line: '{}'".format(line.strip()), 3)

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
            self.debug("Read Header '{}'".format(line), 3)
            if line is None:  # full line not yet received
                return
            if line == '':  # empty line signaling end of headers
                self.debug("All headers received", 3)
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
                self.debug("Received Content of length: {}".format(len(self.request.content)), 3)
                self.request.content_received = True  # mark content as received
            else:  # not yet fully received
                return
        else:  # no content length specified - assuming no content sent
            self.request.content_received = True  # mark content as received
            return  # TODO: Is there a better way to determine for sure whether a request has only a header?

    def send(self, response):
        """ Compiles the response object then adds it to the out_buffer """
        data = response.get_data()
        if data is None:  # error which has been caught, hopefully
            self.error("Request returned no data")
            return
        self.send_raw(data)

    def send_raw(self, data):
        """ Sends raw bytes data as-is to the out_buffer """
        with self.write_lock:  # get lock
            self.out_buffer += data  # add data to buffer
            self.debug("Added data to outgoing buffer", 3)

    def close(self):
        """ Closes the connection """
        self.socket.close()
        self.log("Connection Closed\n")


class ServerHandler(HandlerBase):
    """ Handles incoming requests to a server class """

    def __init__(self, sock, server):
        super().__init__(sock)
        self.server = server     # Server class that created this handler

        self.data_buffer = DataBuffer()   # raw data from stream
        self.image_buffer = DataBuffer()  # data ready to be visually displayed

    def INIT(self, request):
        """ Initial request sent by all streaming clients """
        self.name = request.header['name']
        self.resolution = request.header.get('resolution')
        self.framerate = request.header.get('framerate')

        req = Request()         # Send START request
        self.send_raw(b'stttttoopppppppp')
        #req.add_request('START')
        #req.add_header('useless', 'thing')
        #self.send(req)

    def GET(self, request):
        """ Handle request from web browser """
        response = Request()
        self.debug("Handling request for: '{}'".format(request.path), 2)

        if request.path == '/':
            response.add_response(301)  # redirect
            response.add_header('Location', '/index.html')  # redirect to index.html
            self.send(response)

        elif request.path == '/favicon.ico':
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                img = fout.read()
                response.add_content(img)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'image/x-icon')  # favicon
            response.add_header('Content-Length', len(img))
            self.send(response)

        elif request.path == '/index.html':
            content = self.server.main_page().encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_header('Content-Length', len(content))
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path[1:] in self.server.connections.keys:  # path without '/' is a connection ID
            content = self.server.stream_page(request.path[1:]).encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_header('Content-Length', len(content))
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path.endswitH('stream.mjpg'):  # request for stream
            self.send_multipart()

        else:
            response.add_response(404)  # couldn't find it
            self.send(response)
            self.error("GET requested unknown path", "path: {}".format(request.path))

        self.debug("done handling GET", 3)

    def send_multipart(self):
        """
        Continually creates and sends multipart-type responses to the stream.
        Used to send an image stream to a browser from the image_buffer
        """
        res = Request()
        res.add_response(200)
        res.add_header('Age', 0)
        res.add_header('Cache-Control', 'no-cache, private')
        res.add_header('Pragma', 'no-cache')
        #res.add_header('Connection', 'keep-alive')
        res.add_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.send(res)

        # occurs before every main payload
        header = '--FRAME\r\n'.encode(self.encoding)
        header += 'Content-Type:image/jpeg\r\n\r\n'.encode(self.encoding)  # header with a blank line after562+
        try:
            self.debug("Started multipart stream", 2)
            while True:
                data = self.image_buffer.read()
                packet = header + data + b'\r\n'
                self.send_raw(packet)
        except Exception as e:
            self.error('Browser Stream Disconnected ({}:{})'.format(*self.peer), e)


class ClientHandler(HandlerBase):
    """ Handles incoming requests to a client object """
    def __init__(self, sock, client):
        super().__init__(sock)
        self.client = client      # Client class that created this handler
        self.name = client.name

    def init(self, framerate=None, resolution=None):
        """
        Must call at the end of derived class' __init__ method.
        Send the initial request that lets the server know what type of stream this is.
        Server will respond with the START request.
        May be overwritten, but make sure to include the necessary request line and headers.
        """
        req = Request()
        req.add_request('INIT')  # required
        req.add_header('name', self.name)  # required
        if framerate:
            req.add_header('framerate', framerate)
        if resolution:
            req.add_header('resolution', resolution)
        self.send(req)

    def START(self, request):
        """
        Overwritten by derived class.
        Handles the START request from the server.
        Starts the stream
        """
        pass

    def STOP(self, request):
        """
        Overwritten by derived class.
        Handles the STOP request from the server.
        Stops the stream
        """
        pass


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
            self.message = 'Moved Permanently'
        elif code == 308:
            self.message = 'Permanent Redirect'
        elif code == 404:
            self.message = 'Not Found'
        else:
            self.message = "MESSAGE"

        self.add_header('Server', 'StreamingServer Python/3.7.3')  # TODO: make this not hard coded (Not really necessary yet)
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
            self.debug("Added request line '{}'".format(request_line.strip()), 3)

        if self.code:
            response_line = "{} {} {}\r\n".format(self.version, self.code, self.message)
            data += response_line.encode(self.encoding)
            self.debug("Added response line '{}'".format(response_line.strip()), 3)

        # headers
        for key, value in self.header.items():
            header = "{}: {}\r\n".format(key, value)
            data += header.encode(self.encoding)
            self.debug("Added header '{}:{}'".format(key, value), 3)
        if self.header:
            data += b'\r\n'  # add a blank line to denote end of headers
            self.debug("Added all headers", 3)

        # content
        if self.content:
            data += self.content  # content should already be in bytes
            self.debug("Added content of length: {}".format(len(self.content)), 3)
        else:
            data += b'\r\n'  # if no content, signal end of transmission

        return data


class DataBuffer(object):
    """
    A thread-safe buffer in which to store incoming data
    The write() method can be used by a Picam
    """
    def __init__(self):
        self.data = b''
        self.condition = Condition()

    def read(self):
        with self.condition:
            self.condition.wait()
            return self.data

    def write(self, new_data):
        with self.condition:
            self.data = new_data
            self.condition.notify_all()  # wake any waiting threads

