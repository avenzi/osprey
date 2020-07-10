from io import BytesIO
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
    debug_level = 0  # debugging level
    last_msg = ''    # to keep track of the last output message
    print_lock = Lock()  # lock on output

    def __init__(self, debug=None):
        self.exit = False  # Flag to signal that processes should end
        self.exit_condition = Condition()   # Used to notify throw handling threads when an throw occurs
        if debug is not None:  # given as True or False
            Base.debug_level = debug  # set debug level
            print()  # display message
            print("------------------------------")
            print(":: RUNNING IN DEBUG MODE {} ::".format(Base.debug_level))
            print("------------------------------")

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

    def halt(self):
        """ Signal to end all processes """
        with self.exit_condition:
            self.exit_condition.notify_all()  # wake waiting error threads
            self.exit = True

    def throw(self, message, cause=None):
        """ Display an error message and signal to end all processes """
        self.halt()
        self.display("(ERROR)[{}]: {}".format(threading.currentThread().getName(), message))
        if cause is not None:
            self.display("(CAUSE): {}".format(cause))  # show cause if given

    def traceback(self):
        """ output traceback """
        traceback.print_exc()

    def get_thread_name(self, name):
        """ Given a name, add a unique number to it """
        num = threading.active_count()
        return "Thread[{}]-{}".format(num + 1, name)


class Server(Base):
    """
    Handles incoming connections to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """

    def __init__(self, HandlerClass, port, name='Server', debug=False):
        super().__init__(debug)

        self.HandlerClass = HandlerClass
        self.ip = ''  # ip to bind to
        self.port = port  # port to bind to
        self.name = name  # server name (sent in request headers)
        self.listener = None  # socket that accepts new connections

        self.connections = {}  # index of all connections to the server. (full:address, Handler Object)
        self.max_display_height = 600  # maximum height of images being displayed in a browser stream

    def create(self):
        """ Create a listening socket object """
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address?
            self.listener.bind((self.ip, self.port))  # bind to host address
            self.debug("Socket Bound to *:{}".format(self.port))
        except Exception as e:
            self.throw("Failed to bind socket to *:{}".format(self.port), e)

        try:  # Set as listening connection
            self.debug("Set to listening socket")
            self.listener.listen()
        except Exception as e:
            self.throw("Failed to set as listening socket", e)

    def accept(self):
        """ Accepts new connections and creates a new handler for each """
        try:
            conn, (ip, port) = self.listener.accept()  # wait for a new connection
            conn.setblocking(True)
            self.log("New Connection From: {}:{}".format(ip, port))
        except KeyboardInterrupt:
            self.throw("Manual Termination")
            return
        except Exception as e:
            self.throw("Failed while accepting new connection", e)
            return

        try:
            handler = self.HandlerClass(conn, self)  # create handler with socket
            Thread(target=handler.run, name=self.get_thread_name('Conn'), daemon=True).start()  # run connection on new thread
            self.debug("Completed creation of new handler", 1)
        except Exception as e:
            self.throw("Failed to handle new connection", e)
            return

    def run(self):
        """ Main entry point """
        self.log("Server IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.create()  # create listener socket
        self.log("Listening for connections...")
        while not self.exit:
            self.accept()

    def main_page(self):
        """ Returns the HTML for the main selection page """
        page = """
        <html>
        <head><title>Main Page</title></head>
        <body><h1>Stream Selection</h1>
        """
        for address, conn in self.connections.items():
            if not conn.name:  # if name is not specified, this is a browser connection, not a data streaming connection
                continue
            page += "<p><a href='/{}'>{} ({})</a></p>".format(address, conn.name, address)
        page += "</body></html>"
        return page

    def stream_page(self, ID):
        """ Creates a streaming page """
        conn = self.connections[ID]
        aspect = conn.resolution[0] / conn.resolution[1]
        width = int(aspect * self.max_display_height)
        page = """
        <html>
        <head><title>{name}</title></head>
        <body>
            <h1>{name}</h1>
            <img src="/{stream_id}/stream.mjpg" width="{width}" height="{height}" />
            <a href='/index.html'>Back</a>
        </body>
        </html>
        """.format(name=conn.name, stream_id=ID, width=width, height=self.max_display_height)
        return page
        # TODO: Right now each stream is reached by requesting URL equal to the connection's peer address followed by /stream.mjpg.
        #  For example: /12.345.678.9:1234/stream.mjpg
        #  This is because each connection is identified by it's unique address.
        #  However this is kinda weird, so I would like to implement a different unique identifier that would make this process a but more intuitive.
        #  When I implement this, the method of finding the connection's image_buffer will need to be changed in StreamHandler.GET()
        #  Maybe use a GET query to identify the right stream?


class Client(Base):
    """
    Makes a connection to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """

    def __init__(self, HandlerClass, ip, port, name='Client', debug=False):
        super().__init__(debug)

        self.HandlerClass = HandlerClass
        self.ip = ip  # server ip address to connect to
        self.port = port  # server port to connect through
        self.name = name  # name of client (sent in headers)
        self.socket = None  # socket object

    def create(self):
        """ Create socket object and try to connect to server """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.log("Attempting to connect to {}:{}".format(self.ip, self.port))
            self.socket.connect((self.ip, self.port))
            self.socket.setblocking(True)
            self.log("Socket Connected")
        except Exception as e:
            self.throw("Failed to connect to server", e)
            return

        try:
            conn = self.HandlerClass(self.socket, self)  # create new connection for the client
            self.debug("Completed creation of handler", 1)
            conn.run()  # Only one connection, so no need to thread
        except KeyboardInterrupt:
            self.throw("Manual Termination")
        except Exception as e:
            self.throw("Failed to handle new connection", e)

    def run(self):
        """ Listens for new connections, then starts them on their own thread """
        self.log("Client IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        if not self.exit:
            self.create()


class HandlerBase(Base):
    """
    Inherited by ServerHandler and ClientHandler.
    Object that represents a single connection between server and client.
    Handles incoming requests on a single socket.
    Holds the socket and associated buffers.
    """

    def __init__(self, sock):
        super().__init__()

        self.socket = sock  # socket object to read/write to
        self.peer = "{}:{}".format(*sock.getpeername())  # address of machine on other end of connection

        self.pull_buffer = sock.makefile('rb')  # incoming stream buffer to read from
        self.pull_lock = Condition()  # lock for pull_buffer

        self.push_buffer = sock.makefile('wb')  # outgoing stream buffer to write to
        self.push_lock = Condition()  # lock for push_buffer

        self.request = Request()  # current request being parsed
        self.encoding = 'iso-8859-1'  # encoding for data stream (latin-1)

        # Information sent/received in INIT
        self.name = None  # Name to identify connection. Sent by 'name' header in INIT
        self.framerate = None  # Frame rate of stream, if any. Can be specified by the 'framerate' header in INIT
        self.resolution = (640, 480)  # Default resolution of images. Can be changed by the 'resolution' header in INIT

        self.streaming = False  # flag that indicates whether the connection is currently sending/receiving a multipart stream

    def run(self):
        """ Main entry point - called by parent """
        #Thread(target=self.pull, name=self.get_thread_name("PULL"), daemon=True).start()  # start recv thread
        #Thread(target=self.push, name=self.get_thread_name("PUSH"), daemon=True).start()  # start send thread
        Thread(target=self.handle, name=self.get_thread_name("HANDLE"), daemon=True).start()  # start handler thread

        with self.exit_condition:
            self.exit_condition.wait()  # wait for an throw to be thrown
            self.close()   # close server

    def pull(self):
        """
        Must be run on it's own thread.
        Receive raw bytes from the socket stream and adds to the in_buffer
        """
        while not self.exit:
            try:
                data = self.socket.recv(65536)  # Receive data from stream
                if not data:  # stream disconnected
                    raise Exception
                with self.pull_lock:  # get lock
                    self.pull_buffer.write(data)   # append data to incoming buffer
                    self.pull_lock.notify_all()  # wake threads waiting to read
            except Exception as e:
                self.debug("Pull failed: {}".format(e), 2)
                self.halt()
            else:
                self.debug("Pulled data from stream of length {}: {} ... {}".format(len(data), data[:10], data[len(data)-10:]), 4)

    def push(self):
        """
        Must be run on it's own thread.
        Attempts to send the out_buffer to the stream
        """
        while not self.exit:
            try:
                with self.push_lock:  # get lock
                    while not self.push_buffer:  # wait for push_buffer to be written to
                        self.push_lock.wait()
                    sent = self.socket.send(self.push_buffer)  # try to send as much data from the push_buffer
                    self.debug("Pushed buffer to stream. Length {}: {} ... {}".format(sent, self.push_buffer[:10], self.push_buffer[len(self.push_buffer) - 10:]), 4)
                    self.push_buffer = self.push_buffer[sent:]  # move down buffer according to how much data was sent
            except Exception as e:
                self.debug("Push failed: {}".format(e), 2)
                self.halt()

    def handle(self):
        """
        Must be run on its own thread.
        Pull/Push should be running concurrently, and any requests are handled on new threads.
        Parse requests form the in_buffer, and delegate new threads to handle them.
        """
        while not self.exit:
            while self.streaming:
                with self.pull_lock:
                    self.pull_lock.wait()  # don't handle while streaming

            if not self.parse_request_line():
                continue
            if not self.parse_header():
                continue
            if not self.validate():  # validate request headers before parsing content
                return
            self.parse_content()  # may or may not have content

            if self.request.method:  # received request method
                content_type = self.request.header.get('content-type')
                method_func = getattr(self, self.request.method)  # get handler method that matches name of request method
                if content_type is None:  # no content type - treat method as command
                    self.execute_command(method_func)
                elif content_type.split(';')[0] == 'multipart/x-mixed-replace':  # multipart stream
                    self.streaming = True
                    Thread(target=self.parse_multipart, name=self.get_thread_name("MULTI"), daemon=True).start()
                else:
                    self.throw("Unrecognized content type header", 'content type: {}'.format(content_type))
                self.request = Request()  # ready for new request
            elif self.request.code:  # received a response code
                self.request = Request()  # ready for new request
                pass  # TODO: handle different response codes from clients
            else:
                self.request = Request()  # ready for new request
                self.throw("Unknown request/response type?", "Nether a request method nor a response code were found in the data sent.")

            # TODO: Add a check to see when the thread needs to be stopped?
            #  If the user hasn't written in a natural stopping point, it may be necessary to forcibly kill the thread.

    def validate(self):
        """  Blocks certain user agents. Right now just used to block some random web scraping bot that keeps finding my server """
        hosts = ['fil.hotti.webredirect.org', 'mir.mia.ddnsfree.com']
        agent_keywords = ['nimbostratus', 'cloudsystemnetworks', 'bot']  # keywords to look for in User-Agent header
        host = self.request.header.get('host'),
        agent_string = self.request.header.get('user-agent')
        valid = True
        if host and host in hosts:
            valid = False
        if agent_string:
            for keyword in agent_keywords:
                if keyword in agent_string:
                    valid = False
        if not valid:
            self.throw("Blocked Connection from banned source:\n   Address: {}\n   Host: {}\n   User-Agent: {}".format(self.peer, host, agent_string))
        return valid

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
            - if no CLRF before <length> reached, stop reading and throw throw
        Decode specifies whether to decode the data from bytes to string. If true, also strips whitespace.
        Returns None on throw.
        """
        if line:  # read a single line
            CRLF = b'\r\n'
            data = self.pull_buffer.readline()  # read from stream
            while data and data[-2:] != CRLF and not self.exit:  # doesn't end in newline
                data += self.pull_buffer.readline()  # keep adding
                data_len = len(data)
                if data_len > length:  # data too big - newline not found before maximum
                    prev = 20 if data_len > 40 else int(data_len/2)
                    self.throw("Couldn't read a line from the stream - maximum length reached (max:{}, length:{})".format(length, data_len), "{} ... {}".format(data[prev:], data[data_len-prev:]))
                    return

        else:  # exact length specified
            data = self.pull_buffer.read(length)
            data_len = len(data)
            while data and data_len < length and not self.exit:  # didn't get full length
                length -= data_len
                data += self.pull_buffer.read(length)  # pull remaining length
                data_len = len(data)

        if not data:  # no data read - disconnected
            self.halt()
            return
        if decode:
            data = data.decode(self.encoding).strip()  # decode and strip whitespace including CLRF
        return data

    def parse_request_line(self):
        """
        Parses the Request-line of a request, finding the request method, path, and version strings.
        Return True if found, False if not
        """
        max_len = 256  # max length of request-line before throw (arbitrary choice)

        line = ''
        while line == '':  # if blank lines are read, keep reading.
            line = self.read(max_len, line=True)  # read first line from stream
            if line is None:  # error reading
                return False
            self.debug("Received Request-Line: '{}'".format(line.strip()), 3)

        words = line.split()
        if len(words) != 3:
            err = "Request-Line must conform to HTTP Standard ( METHOD /path HTTP/X.X   or   HTTP/X.X STATUS MESSAGE )"
            self.throw(err, line)
            return False
        # TODO: maybe add compatibility with shorter response lines without a version

        if words[0].startswith("HTTP/"):  # response
            self.request.version = words[0]
            self.request.code = words[1]
            self.request.message = words[2]
        else:  # request
            self.request.method = words[0]
            self.request.path = words[1]
            self.request.version = words[2]

        if self.request.method and not hasattr(self, self.request.method):  # if a method for the request doesn't exist
            self.throw('Unsupported Request Method', "'{}'".format(self.request.method))
            return False
        return True

    def parse_header(self):
        """
        Fills the header dictionary from the received header text.
        Return True if all are found, False if not
        """
        max_num = 32  # max number of headers (arbitrary choice)
        max_len = 1024  # max length each header (arbitrary choice)
        for _ in range(max_num):
            line = self.read(max_len, line=True)  # read next line in stream
            self.debug("Read Header '{}'".format(line), 3)
            if line is None:  # error reading
                return False
            if line == '':  # empty line signaling end of headers
                self.debug("All headers received", 3)
                self.request.header_received = True  # mark header as received
                break
            try:
                key, val = line.split(':', 1)  # extract field and value by splitting at first colon
            except ValueError:
                self.throw("Header line did not match standard format.", "Line: {}".format(line))
                return False

            self.request.header[key.lower()] = val.strip()  # remove extra whitespace from value
        else:
            self.throw("Too many headers", "> {}".format(max_num))
            return False
        return True

    def parse_content(self):
        """
        Parse request payload, if any.
        Return True if all are found, False if not
        """
        length = self.request.header.get("content-length")
        if length:  # if content length was sent
            content = self.read(int(length), decode=False)  # read raw bytes from stream
            if content is None:   # error reading
                return False
            self.debug("Received Content of length: {}".format(len(content)), 3)
            self.request.content = content
            return True
        else:  # no content length specified - assuming no content sent
            return False
            # TODO: Is there a better way to determine for sure whether a request has only a header?

    def execute_command(self, method):
        """ Calls the given method on a new thread within the connection """
        method_thread = Thread(target=method, args=(self.request,), name=self.get_thread_name(method.__name__), daemon=True)
        method_thread.start()

    def send(self, response):
        """ Compiles the response object then adds it to the out_buffer """
        data = response.get_data()
        if data is None:  # throw which has been caught, hopefully
            self.throw("Request returned no data")
            return
        self.send_raw(data)

    def send_raw(self, data):
        """ Sends raw bytes data as-is to the out_buffer """
        self.push_buffer.write(data)
        self.push_buffer.flush()
        self.debug("Added data to outgoing buffer", 3)

    def send_multipart(self, buffer, request=None):
        """
        Continually creates and sends multipart-type responses to the stream.
        Used to send an image stream from an image_buffer
        NOTE:
            - If sending a stream to a browser, do not specify a request object.
            - If sending a stream to another connection object, use a request
                object to send a request method denoting which function to call
                for every data chunk sent - i.e. use add_request().
                Extra headers may also be added with add_header().
        """
        chunk_header = b'--DATA\r\n'  # sent along with every data chunk

        if not request:  # if no request is specified, assume a response header used to initially respond to browser requests.
            request = Request()
            request.add_response(200)
            request.add_header('Age', 0)
            request.add_header('Cache-Control', 'no-cache, private')
            # res.add_header('Connection', 'keep-alive')

            chunk_header += b'content-type:image/jpeg\r\n'  # when sending to browser, always use jpeg image type in the chunk headers

        request.add_header('content-type', 'multipart/x-mixed-replace; boundary=DATA')
        request.add_content('')
        self.send(request)

        try:
            self.debug("Started multipart stream", 1)
            self.streaming = True
            while not self.exit and self.streaming:
                data = buffer.read()
                length_header = "Content-Length:{}\r\n".format(len(data)).encode(self.encoding)  # content length + blank line
                packet = chunk_header + length_header + b'\r\n' + data + b'\r\n'
                self.send_raw(packet)
            self.debug("Ended multipart stream", 1)
        except Exception as e:
            self.throw('Multipart Stream Disconnected ({})'.format(self.peer), e)
        finally:
            self.streaming = False

    def close(self):
        """ Closes the connection """
        self.exit = True  # set exit status if not set already
        self.socket.close()
        self.log("Connection Closed ({})\n".format(self.peer))


class ServerHandler(HandlerBase):
    """ Handles incoming requests to a server class """

    def __init__(self, sock, server):
        super().__init__(sock)
        self.server = server  # Server class that created this handler
        self.name = None  # connection name. Serves also to determine whether this is a data-collection connection. Browser streams do not have a name

        self.data_buffer = DataBuffer()  # raw data from stream
        self.image_buffer = DataBuffer()  # data ready to be visually displayed

        self.server.connections[self.peer] = self  # add this connection to the server's index

    def close(self):
        super().close()
        del self.server.connections[self.peer]  # remove this connection from the server's index

    def INIT(self, request):
        """ Initial request sent by all streaming clients """
        self.name = request.header['name']
        self.resolution = tuple((int(i) for i in request.header.get('resolution').split('x')))
        self.framerate = request.header.get('framerate')

        req = Request()  # Send START request
        req.add_request('START')
        req.add_header('useless', 'thing')
        self.send(req)

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

        elif request.path[1:] in self.server.connections.keys():  # if path without '/' is a connection ID
            content = self.server.stream_page(request.path[1:]).encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_header('Content-Length', len(content))
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path.endswith('stream.mjpg'):  # request for stream
            ID = request.path[1:len(request.path) - len('/stream.mjpg')]  # get connection ID from the path
            buffer = self.server.connections[ID].image_buffer  # image buffer of connection
            self.send_multipart(buffer)

        else:
            response.add_response(404)  # couldn't find it
            self.send(response)
            self.log("GET requested unknown path: {}".format(request.path))

        self.debug("done handling GET", 3)

    def parse_multipart(self):
        """ parses a multipart stream created by send_multipart. Additionaly calls the given method for each data chunk """
        try:
            boundary = False
            headers = False
            length = None
            while not self.exit and self.streaming:
                if not boundary:
                    boundary_header = self.read(32, line=True)
                    if boundary_header == '':
                        continue
                    self.debug("Boundary line: {}".format(boundary_header), 3)
                    boundary = True
                elif not headers:
                    for _ in range(5):
                        line = self.read(256, line=True)  # read next line in stream
                        self.debug("Read Chunk Header '{}'".format(line), 3)
                        if line == '':  # empty line signaling end of headers
                            self.debug("All chunk headers received", 3)
                            headers = True  # mark header as received
                            break
                        key, val = line.split(':', 1)  # extract field and value by splitting at first colon
                        if key.lower() == 'content-length':
                            length = int(val)
                    else:
                        self.throw("Too many headers", "> {}".format(5))
                        break
                else:
                    if not length:
                        self.throw("Did not receive content-length header")
                        return
                    data = self.read(length, decode=False)
                    self.image_buffer.write(data)
                    self.debug("Wrote to image buffer", 3)
                    boundary = False
                    headers = False
                    length = None
            self.streaming = False
        except Exception as e:
            self.throw("BAD", e)


class ClientHandler(HandlerBase):
    """ Handles incoming requests to a client object """

    def __init__(self, sock, client):
        super().__init__(sock)
        self.client = client  # Client class that created this handler
        self.name = client.name

        self.data_buffer = DataBuffer()  # raw data from device

    def init(self, **headers):
        """
        Call at initialization (or in start() function).
        specify any headers that are to be sent.
        Send the initial request that lets the server know what type of stream this is.
        Server will respond with the START request.
        """
        req = Request()
        req.add_request('INIT')
        req.add_header('name', self.name)
        for key, val in headers.items():
            req.add_header(key, val)
        self.send(req)
        # TODO: Make this more modular. Allow user to specify what information is being sent?

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
        self.encoding = 'iso-8859-1'  # byte encoding
        # TODO: make encoding not hard-coded? It's defined again in the Handler class. Maybe there's a nice way to pass it down? putting it in the constructor would not be ideal because the user has to call it in custom request methods.

        self.method = None  # request method (GET, POST, etc..)
        self.path = None  # request path
        self.version = None  # request version (HTTP/X.X)
        self.header = {}  # dictionary of headers
        self.content = None  # request content in bytes

        self.request_received = False  # whether the whole request line has been received
        self.header_received = False  # whether all headers have been received
        self.content_received = False  # whether all content has been received

        self.code = None  # HTTP response code
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
            self.message = 'MESSAGE'

        self.add_header('Server', 'StreamingServer Python/3.7.3')  # TODO: make this not hard coded (Not really necessary yet)
        self.add_header('Date', self.date())

    def add_header(self, keyword, value):
        """ Add a single header line """
        self.header[keyword.lower()] = value

    def add_content(self, content):
        """ Add main content payload """
        if type(content) == str:
            data = content.encode(self.encoding)  # encode if string
        elif type(content) == bytes:
            data = content
        else:  # type conversion not implemented
            self.throw("Cannot send content - type not accounted for.", type(content))
            return
        self.content = data

    def verify(self):
        """ Verify that this object meets all requirements and can be safely sent to the stream """
        if self.method and self.code:  # trying to send both a response and a request
            self.throw("Cannot send both a response and a request", 'You added request method "{}" and response code "{}"'.format(self.method, self.code))
            return False
        if not self.method and not self.code and self.header:
            self.throw("If you send a header, you must include a request or response as well")
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
        if self.content is not None:
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

