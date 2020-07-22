from io import BytesIO
import socket
import time
import traceback
import threading
from threading import Thread, Lock, Condition
from requests import get
import inspect
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


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
        self.exit = True
        self.streaming = False
        with self.exit_condition:
            self.exit_condition.notify_all()  # wake waiting error threads

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

    def __init__(self, port, name='Server', debug=False):
        super().__init__(debug)

        self.HandlerClass = InitServerHandler   # initial class to handle incoming INIT requests
        self.ip = ''      # ip to bind to
        self.port = port  # port to bind to
        self.name = name  # server name
        self.listener = None  # socket that accepts new connections

        self.connections = {}  # index of all connections to the server. (full:address, Handler Object)

    def create(self):
        """ Create a listening socket object """
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address?
            self.listener.bind((self.ip, self.port))  # bind to host address
            self.debug("Socket Bound to *:{}".format(self.port))
        except Exception as e:
            self.throw("Failed to bind socket to *:{}".format(self.port), e)
            return

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
        except Exception as e:
            self.throw("Failed while accepting new connection", e)
            return

        try:
            handler = self.HandlerClass(conn, self)  # create handler with new socket
            Thread(target=handler.run, name=self.get_thread_name("INIT-RUN"), daemon=True).start()  # run connection on new thread
        except Exception as e:
            self.throw("Failed to handle new connection", e)
            return

    def run(self):
        """ Main entry point """
        self.log("Server IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.create()  # create listener socket
        if not self.exit:
            self.log("Listening for connections...")
        while not self.exit:
            try:
                self.accept()  # accept new connections and handle on new daemon thread
            except KeyboardInterrupt:
                self.throw("Manual Termination")
                self.close()
                return

    def close(self):
        """ Makes sure each connection closes before terminating main thread """
        for handler in list(self.connections.values()):  # force as list instead of iterator because connections remove themselves as they are closed
            handler.halt()  # signal handler to exit
            handler.thread.join()  # wait for it to exit
        self.log("All connections terminated")

    def main_page(self):
        """ Returns the HTML for the main selection page """
        page = """
        <html>
        <head><title>Data Hub</title></head>
        <body><h1>Stream Selection</h1>
        """
        # TODO: Organize connections by host device
        for address, conn in self.connections.items():
            if not conn.name:  # if name is not specified, this is a browser connection, not a data streaming connection
                continue
            page += "<p><a href='/{}'>{} ({})</a></p>".format(address, conn.name, address)
        page += "</body></html>"
        return page


class Client(Base):
    """
    Makes a connection to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """

    def __init__(self, ip, port, name='Unnamed Client', debug=False):
        super().__init__(debug)

        self.ip = ip  # server ip address to connect to
        self.port = port  # server port to connect through
        self.name = name  # name of client
        self.socket = None  # socket object

        self.connections = []  # list of handlers on this client

    def create(self, handler_class):
        """ Create socket object and try to connect it to the server, then run the handler class on a new thread. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.debug("Attempting to connect to server", 2)
            self.socket.connect((self.ip, self.port))
            self.socket.setblocking(True)
            self.debug("Socket Connected", 2)
        except Exception as e:
            self.log("Failed to connect to server: {}".format(e))
            return False

        try:
            handler = handler_class(self.socket, self)  # create new connection for the client
            Thread(target=handler.run, name=self.get_thread_name("RUN"), daemon=True).start()  # start handler on new thread
            self.connections.append(handler)
            self.debug("Created Handler '{}'".format(handler.name), 2)
        except Exception as e:
            self.log("Failed to create new handler: {}".format(e))
            return False
        return True

    def run(self, handlers):
        """
        Takes in a list of Handler CLasses to use.
        Creates one instance of each handler type.
        For each handler class, listens for new connections then starts them on their own thread.
        """
        self.log("Name: {}".format(self.name))
        self.log("Device IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.log("Server IP: {}".format(self.ip))
        for handler_class in handlers:
            if not self.create(handler_class):  # connect to server and handle on new thread
                self.log("Terminating")
                return
        try:
            with self.exit_condition:
                self.exit_condition.wait()  # wait until exit condition notified
        except KeyboardInterrupt:
            self.throw("Manual Termination")
        except Exception as e:
            self.throw("Client terminated due exception", e)
        finally:
            self.close()  # terminate

    def close(self):
        """ Makes sure each connection closes before terminating main thread """
        for handler in self.connections:
            handler.halt()  # signal handler to exit
            handler.thread.join()  # wait for it to exit
        self.log("All connections terminated")


class HandlerBase(Base):
    """
    Inherited by ServerHandler and ClientHandler.
    Object that represents a single connection between server and client.
    Handles incoming requests on a single socket.
    Holds the socket and associated buffers.
    """

    def __init__(self, sock):
        super().__init__()

        self.socket = sock                               # socket object to read/write to
        self.thread = None                               # thread calling this handler's run() method

        self.ip = "{}:{}".format(*sock.getsockname())    # address of this socket
        self.peer = "{}:{}".format(*sock.getpeername())  # address of machine on other end of connection
        self.name = None                                 # name of connection

        self.pull_buffer = sock.makefile('rb')  # incoming stream buffer to read from
        self.pull_lock = Condition()            # lock for pull_buffer

        self.push_buffer = sock.makefile('wb')  # outgoing stream buffer to write to
        self.push_lock = Condition()            # lock for push_buffer

        self.request = Request()      # current request being parsed
        self.encoding = 'iso-8859-1'  # encoding for data stream (latin-1)

        self.name = None  # Name to identify connection. Sent by 'name' header in INIT
        self.streaming = False  # flag that indicates whether the connection is currently sending/receiving a multipart stream

    def run(self):
        """
        Main entry point.
        Called by parent as a non-daemon thread.
        Starts handling on a new thread.
        Waits for an error to be thrown, then closes socket.
        """
        self.thread = threading.current_thread()  # set running thread
        Thread(target=self.handle, name=self.get_thread_name("HANDLE"), daemon=True).start()  # start handler thread
        try:
            with self.exit_condition:
                self.exit_condition.wait()  # wait for self.halt()
        except Exception as e:
            self.debug("Termination in handler: {}".format(e))
        finally:
            self.close()

    def handle(self):
        """
        Must be run on its own thread.
        Parse requests form the stream, and delegate new threads to handle them.
        """
        while not self.exit:
            #while self.streaming:
                #with self.pull_lock:
                    #self.pull_lock.wait()  # don't handle while streaming
            if not self.parse_request_line():
                continue
            if not self.parse_header():
                continue
            if not self.validate():  # validate request headers before parsing content
                return
            self.parse_content()  # may or may not have content

            if self.request.method:  # received request method
                if not hasattr(self, self.request.method):  # if a method for the request doesn't exist
                    self.throw('Unsupported Request Method', "'{}'".format(self.request.method))
                    return
                content_type = self.request.header.get('content-type')
                method_func = getattr(self, self.request.method)  # get handler method that matches name of request method
                if content_type is None:  # no content type - treat method as command
                    self.execute_command(method_func)
                    if self.request.method == 'INIT':
                        self.debug("Halting after INIT request", 3)
                        self.halt()  # stop after INIT method called. Handling is now done in a different class.
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
        """
        Looks for keywords in the Host and User-Agent headers.
        Right now just used to block some random web scraping bots that keep finding my server
        """
        host_keywords = ['webredirect', 'ddnsfree']
        agent_keywords = ['nimbostratus', 'cloudsystemnetworks', 'bot']  # keywords to look for in User-Agent header
        host_string = self.request.header.get('host'),
        agent_string = self.request.header.get('user-agent')
        valid = True
        if host_string:
            for keyword in host_keywords:
                if keyword in host_string:
                    valid = False
        if agent_string:
            for keyword in agent_keywords:
                if keyword in agent_string:
                    valid = False
        if not valid:
            self.throw("Blocked Connection from banned source:\n   Address: {}\n   Host: {}\n   User-Agent: {}".format(self.peer, host_string, agent_string))
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
        Returns None on error.
        """
        try:
            if line:  # read a single line
                CRLF = b'\r\n'
                data = self.pull_buffer.readline()  # read from stream
                while data and data[-2:] != CRLF and not self.exit:  # doesn't end in newline
                    data += self.pull_buffer.readline()  # keep adding
                    data_len = len(data)
                    if data_len > length:  # data too big - newline not found before maximum
                        prev = 20 if data_len > 40 else int(data_len/2)
                        self.throw("Couldn't read a line from the stream - maximum length reached (max:{}, length:{})".format(length, data_len), "{} ... {}".format(data[prev:], data[data_len-prev:]))
                        raise BrokenPipeError
            else:  # exact length specified
                data = self.pull_buffer.read(length)
                data_len = len(data)
                while data and data_len < length and not self.exit:  # didn't get full length
                    length -= data_len
                    data += self.pull_buffer.read(length)  # pull remaining length
                    data_len = len(data)
            if not data:  # no data read - disconnected
                raise BrokenPipeError
            if decode:
                data = data.decode(self.encoding).strip()  # decode and strip whitespace including CLRF
            return data
        except (ConnectionResetError, BrokenPipeError) as e:  # disconnected
            self.halt()
            return

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
        if data is None:  # error which has been caught, hopefully
            self.throw("Request returned no data")
            return
        self.send_raw(data)

    def send_raw(self, data):
        """ Sends raw bytes data as-is to the out_buffer """
        try:
            self.push_buffer.write(data)
            self.push_buffer.flush()
            self.debug("Pushed data to stream", 3)
        except (ConnectionResetError, BrokenPipeError) as e:
            self.halt()

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
            self.debug("Started multipart stream", 2)
            self.streaming = True
            while not self.exit and self.streaming:
                data = buffer.read()
                length_header = "Content-Length:{}\r\n".format(len(data)).encode(self.encoding)  # content length + blank line
                packet = chunk_header + length_header + b'\r\n' + data + b'\r\n'
                self.send_raw(packet)
            self.debug("Ended multipart stream", 2)
        except Exception as e:
            self.throw('Multipart Stream Disconnected ({})'.format(self.peer), e)
        finally:
            self.streaming = False

    def close(self):
        """ Closes the connection """
        self.exit = True  # set exit status if not set already
        self.socket.close()


class ServerHandler(HandlerBase):
    """
    Base class for all derived Server Handler classes in ingestion_lib.
    """

    def __init__(self, sock, server):
        super().__init__(sock)
        self.server = server  # Server class that created this handler
        self.client_name = None  # device name at the other end of this connection

        self.data_buffer = DataBuffer()   # raw data from stream
        self.image_buffer = DataBuffer()  # data ready to be visually displayed in a browser

        self.server.connections[self.peer] = self  # add this connection to the server's index

    def INIT(self, request):
        """
        Overwritten in derived classes
        Handles initial sign-on request from clients.
        """
        pass

    def INGEST(self, request):
        """
        Overwritten in derived classes
        Parses the content of the request and stores it in data_buffer.
        Additionally can create a visual representation of the data to be stored in image_buffer.
        """
        pass

    def HTML(self):
        """
        Overwritten in derived classes
        Returns the HTML string for a browser page displaying the content being streamed
        """
        pass

    def parse_multipart(self):
        """ parses a multipart stream created by send_multipart. Additionaly calls the given method for each data chunk """
        self.debug("Receiving multipart stream", 2)
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

    def close(self):
        super().close()  # close connection normally
        del self.server.connections[self.peer]  # remove this connection from the server's index
        self.log("Connection Closed: {} ({})".format(self.name, self.peer))


class InitServerHandler(HandlerBase):
    """
    Class to handle INIT requests from new connections.
    Uses information from INIT request to hand the connection
        over to the specified ServerHandler derived class.
    Also handles GET requests from browsers.
    """
    def __init__(self, sock, server):
        super().__init__(sock)
        self.server = server  # Server class that created this handler

    def INIT(self, request):
        """
        Handle initial request sent by all streaming clients.
        Pass request onto specified Handler class
        """
        handler_name = request.header.get('class')  # connection requests a specific Handler class to be used

        # get the class with name handler_name
        import ingestion_lib
        HandlerClass = [member[1] for member in inspect.getmembers(ingestion_lib, inspect.isclass) if (member[1].__module__ == 'ingestion_lib' and member[0] == handler_name)][0]
        handler = HandlerClass(self.socket, self.server)  # create new handler

        Thread(target=handler.run, name=self.get_thread_name('RUN'), daemon=True).start()  # run new handler
        Thread(target=handler.INIT, args=(request,), name=self.get_thread_name('INIT'), daemon=True).start()  # pass on this request to the new handler's INIT method
        self.debug("Initial handler passed request to '{}'".format(handler.__class__.__name__), 2)

    def GET(self, request):
        """ Handle request from web browser """
        response = Request()
        self.debug("Handling request for: '{}'".format(request.path), 1)

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
            self.send(response)

        elif request.path == '/index.html':
            content = self.server.main_page().encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_content(content)  # write html content to page
            self.send(response)

        elif request.path[1:] in self.server.connections.keys():  # if path without '/' is a connection ID
            #                        connections index is ip    custom HTML() page generation
            content = self.server.connections[request.path[1:]].HTML().encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
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

    def close(self):
        super().close()
        self.debug("Initial request handler closed", 2)


class ClientHandler(HandlerBase):
    """ Handles incoming requests to a client object """

    def __init__(self, sock, client):
        super().__init__(sock)
        self.client = client  # Client class that created this handler
        self.server_name = None  # name of server at the other end of this connection

        self.data_buffer = DataBuffer()  # raw data from device

    def init(self):
        """
        Overwritten by derived classes.
        Must call on initialization.
        Send sign-on request to server.
        Gives the server necessary information about this connection.
        Server will respond with the START request.
        """
        pass

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

    def close(self):
        super().close()
        self.streaming = False  # stop streaming
        self.log("Closed {}".format(self.name))
        with self.client.exit_condition:
            self.client.exit_condition.notify_all()  # wake waiting thread in client to terminate it


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
        if content:
            self.add_header('content-length', len(data))  # add content length header
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


class Graph:
    """
    Dynamic graph using matplotlib to data can be appended.
    Used to create and update plot images sent to a browser to be viewed.
    """
    def __init__(self, rows, cols, domain):
        """
        Initialize a graph with axes arranges in rows, cols.
        think of this as a wrapper for plt.subplots()
        Domain is the range of x values that can be seen on the graph before at a time.
        """
        self.rows = rows
        self.cols = cols
        self.domain = domain
        matplotlib.rcParams.update({'font.size': 15})
        matplotlib.rcParams.update({'figure.autolayout': True})  # plt.tight_layout()
        self.ax = plt.subplots(rows, cols, figsize=(10*cols, 3*rows), dpi=100)[1]
        self.aspect = {'width': 100*10*cols, 'height': 100*3*rows}  # image dimensions

        self.lock = Condition()  # threading lock for the data

        plt.tight_layout(pad=2)
        for i in range(rows):
            for j in range(cols):
                ax = self.ax[i, j]
                ax.set_autoscaley_on(True)  # TODO: Add option to set specific y range instead
                ax.xaxis.set_visible(False)
                ax.grid(which='major', axis='y')
                self.ax[i, j] = Axes(ax, self.domain)  # wrap in custom axes object

    def save(self, buffer):
        """ Save the plot as an image into a DataBuffer """
        for i in range(self.rows):
            for j in range(self.cols):
                self.ax[i, j].rescale()
        plt.savefig(buffer, format='jpeg', dpi=50, pil_kwargs={'quality':90})


class Axes:
    """
    Wrapper for matplotlib AxesSubplot
    Allows for axis data to be dynamically updated and re-drawn.
    <mode> is the method of dynamically determining the range of the y-axis. Use set_mode() to set.
        - 'tight' fits the y-axis range to the data currently on the plot
        - 'max' keeps the y-axis range at the max/min values reached thus far
        - 'fixed' sets the y-axis to a constant range, set by <yrange>, a tuple of floats.
    """
    def __init__(self, ax, domain):
        self.ax = ax      # matplotlib AxesSubplot object
        self.lines = {}   # label:line2D
        self.domain = domain  # int maximum number of x values to plot before removing old data
        self.mode = 'tight'
        self.range = ()       # tuple of floats - the range of the y-axis.

    def set_domain(self, domain):
        """ Set range of x values to keep """
        self.domain = domain

    def set_mode(self, mode, yrange=None):
        """ Set the mode of determining the y-axis range """
        self.mode = mode
        if mode == 'fixed':
            self.ax.set_ylim(yrange)  # if in fixed mode, set ylim once

    def set_title(self, title):
        """ Set axes title """
        self.ax.set_title(title)

    def set_ylabel(self, title):
        """ Sets the label on the y-axis """
        self.ax.set_ylabel(title)

    def rescale(self):
        """ Rescale axes """
        if self.mode == 'max':
            self.ax.set_ylim(self.range)
        self.ax.relim()
        self.ax.autoscale_view()

    def update_range(self, y):
        """ Updates the y-axis range based on the given mode and the new X and Y data (lists) """
        if self.mode == 'max':
            if self.range:
                self.range = (min(self.range[0], min(y)), max(self.range[1], max(y)))
            else:
                self.range = (min(y), max(y))

    def add_lines(self, *labels):
        """ Add a labelled plot to a particular axis location """
        for label in labels:
            self.lines[label] = self.ax.plot([], label=label)[0]  # add label:line2D to lines dict

    def add_legend(self):
        """ Adds a legend to the axis """
        self.ax.legend(loc='upper left')  # position outside upper right of plot

    def add_data(self, label, x, y):
        """ Add list of data to plot. X and Y must both be lists"""
        # TODO: More efficient way to do this? Maybe use a queue.
        self.update_range(y)  # update y-axis range
        line = self.lines[label]
        if len(line.get_xdata()) > self.domain:  # old data out of range
            xdata = np.roll(line.get_xdata(), -len(x))  # shift data to the left by the length of new data
            ydata = np.roll(line.get_ydata(), -len(x))
            for i in range(len(x)):
                pos = (len(xdata)-len(x)) + i
                xdata[pos] = x[i]  # set new values
                ydata[pos] = y[i]
                ydata[pos] = y[i]
        else:  # append to data
            xdata = np.append(line.get_xdata(), x)
            ydata = np.append(line.get_ydata(), y)
        line.set_xdata(xdata)
        line.set_ydata(ydata)


