from requests import get
import socket
import json
import inspect
import time

from bokeh.embed import json_item
from ..lib import Base, HostNode, WorkerNode, SocketHandler, HTTPRequest, HTTPResponse

PAGES_PATH = 'lib/server/pages'
CONFIG_PATH = 'lib/server/config.json'


class Server(HostNode):
    """
    Handles all incoming connections to the server.
    INIT requests from new connections create a new WorkerConnection object to handle all subsequent requests.
    GET requests from browsers are handled to server server page contents.
    Any other request with a query matching one of the current Connections is handed over to that Connection.
    Call run() to start.
    """
    def __init__(self, debug=0):
        with open(CONFIG_PATH, 'r') as file:  # get config settings
            config = json.load(file)

        name = config['NAME']
        super().__init__(name, auto=False)

        self.ip = ''                # ip to bind to
        self.host_ip = ''           # public ip
        self.port = config.get('PORT')  # port to bind to
        self.data_path = config.get('DATA_PATH')  # path to data directory
        self.set_log_path(config.get('LOG_PATH'))  # path to logging directory

        self.listener = None  # socket that accepts new connections
        self.set_debug(debug)

    def _run(self):
        """
        Called by self.run() on a new thread
        Creates server socket and listens for new connections.
        New sign-on requests from clients create new worker node.
        Handles server-specific requests, on the main process, and passes
            client-specific requests onto the respective worker processes
        """
        self.host_ip = '{}:{}'.format(get('http://ipinfo.io/ip').text.strip(), self.port)
        self.log("Server Host: {}".format(self.host_ip))  # show this machine's public ip
        self.create_listener()  # create listener socket

        # run accept-loop
        while not self.exit:
            self.accept()

    def create_listener(self):
        """ Create a listening socket """
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # Bind socket to ip and port
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address
            self.listener.bind((self.ip, self.port))  # bind to host address
            self.debug("Server Socket Bound to *:{}".format(self.port), 2)
        except Exception as e:
            self.throw("Failed to bind server socket to *:{}".format(self.port), e)
            return

        try:  # Set as listening connection
            self.listener.listen()
            self.debug("Set to listening socket", 2)
        except Exception as e:
            self.throw("Failed to set as listening socket", e)
            return

        self.log("Listening for connections...")

    def accept(self):
        """ Accepts new connections and runs a new handler for each """
        try:
            new_socket, (ip, port) = self.listener.accept()  # wait for a new connection
            new_socket.setblocking(True)
            #self.debug("New Connection From: {}:{}".format(ip, port), 2)
        except Exception as e:
            self.throw("Failed while accepting new connection", e, trace=True)
            return

        try:
            new_handler = SocketHandler(new_socket, self)
            sock_id = self.add_socket(new_handler)  # add new socket to index and run it
            self.sockets[sock_id].run()  # run the new socket
        except Exception as e:
            self.throw("Failed to handle create new SocketHandler", e, trace=True)
            return

    def HANDLE(self, request, threaded=True):
        """
        Overwrites default method to handle incoming requests
        When a request would normally be handled, first decide if it should be handled by an existing connection.
        This is determined by whether a connection ID was specified in the query string of the request.
        """
        ID = request.queries.get('id')  # handler ID, if present in the request querystring

        if ID is not None:  # a particular worker was specified to handle this request
            pipe = self.pipes.get(ID)  # Pipe to worker with this ID
            if pipe:  # Pipe exists
                self.transfer_socket(pipe, request.origin, request)  # transfer origin socket and request to the existing Worker Node
                return
            else:  # Pipe doesn't exist
                self.debug("A client requested an invalid ID: {}".format(request))
                #self.debug("Valid ID's: {}".format(list(self.pipes.keys())))

        # no ID was specified or ID not found - continue to run on this Server HostNode
        if request.method == "SIGN_ON":  # reserved method for initializing new data stream client connections
            super().HANDLE(request, threaded=False)  # call SIGN_ON method, and don't read any more from the socket
        else:
            super().HANDLE(request, threaded=threaded)  # call the method per usual

    def SIGN_ON(self, request):
        """
        Reserved method for clients to sign onto the server. Should not be overwritten.
        Handle initial sign-on request sent by all streaming clients.
        Creates a new Connection class specified by the request.
        Transfers the request to the new Connection class to finish initialization.
        """
        class_name = request.header.get('class')
        device_name = request.header.get('device')
        display_name = request.header.get('name')
        if not class_name:
            self.throw("New data-client SIGN_ON request failed to specify the name of the class with which to handle the request. \
                The class name must be sent as the 'class' header.", "Request: {}".format(request))
            return
        if not device_name:
            self.debug("New data-client INIT request did not specify the name of the device hosting the connection. Must be sent as the 'device' header.")
        if not display_name:
            self.debug("New data-client INIT request did not specify the display name of the connection. Must be sent as the 'name' header. This will default to the Connection class name")

        # Get the right handler class from handlers.py
        try:
            from . import handlers  # imported here so as to avoid import recursion
        except:
            self.throw("Error importing Handlers", trace=True)
            return

        members = inspect.getmembers(handlers, inspect.isclass)  # all classes [(name, class), ]
        HandlerClass = None
        for member in members:
            if member[1].__module__.split('.')[-1] == 'handlers' and member[0] == class_name:  # class name matches
                HandlerClass = member[1]
                break
        if not HandlerClass:
            self.throw("Handler Class '{}' not found in handlers.py".format(class_name))
            return

        # TODO: If we want the stream to start automatically as soon as it's connected, this is a good place to do it
        # start_req = HTTPRequest()
        # start_req.add_request('START')
        # self.send(start_req, request.origin)  # send start request back to client
        self.log("New connection from {} on {} ({})".format(display_name, device_name, request.origin.peer))

        worker = HandlerClass()  # create new worker node
        worker.name = display_name
        worker.device = device_name

        request.origin.halt()     # stop running this socket
        worker.set_source(request.origin.socket)  # extract the raw socket and set it as the new source
        self.remove_socket(request.origin.id)  # remove the handler from this node
        self.run_worker(worker)   # run the Worker on a new process

    def GET(self, request):
        """ Handle GET request from web browser """
        response = HTTPRequest()

        if request.path == '/':
            response.add_response(301)  # redirect
            response.add_header('Location', '/index.html')  # redirect to index.html

        elif request.path == '/favicon.ico':
            response.add_response(200)  # success
            response.add_header('Content-Type', 'image/x-icon')  # favicon
            with open(PAGES_PATH+'/favicon.ico', 'rb') as file:  # send favicon image
                img = file.read()
                response.add_content(img)

        elif request.path == '/index.html':
            content = self.main_page().encode(self.encoding)
            response.add_response(200)  # success
            response.add_header('Content-Type', 'text/html')
            response.add_content(content)  # write html content to page

        elif request.path == '/command':
            command = request.queries.get('command')

        elif request.path == '/404.html':
            response.add_response(200)
            response.add_header('Content-Type', 'text/html')
            with open(PAGES_PATH+'/404.html', 'rb') as file:
                response.add_content(file.read())

        elif request.path == '/invalid_id.html':
            response.add_response(200)
            response.add_header('Content-Type', 'text/html')
            with open(PAGES_PATH+'/invalid_id.html', 'rb') as file:
                response.add_content(file.read())

        else:  # unknown path
            response.add_response(301)  # redirect
            if request.queries.get('id'):  # id was provided, but was invalid.
                response.add_header('location', '/invalid_id.html')
            else:  # no id was provided
                response.add_header('location', '/404.html')
                self.log("A client requested unknown path: {}".format(request.path))

        self.send(response, request.origin)  # send response back to requesting socket

    def OPTIONS(self, request):
        """ Responds to an OPTIONS request """
        self.log("A client requested OPTIONS")
        response = HTTPRequest()
        response.add_response(405)
        self.send(response, request.origin)

    def main_page(self):
        """ Returns the HTML for the main selection page """
        # Organize connections by host device
        devices = {}  # {device: [(id,name), (id,name), ...], ...}
        ids = []  # list of all connected stream ID's
        for id, pipe in self.pipes.items():
            if devices.get(pipe.device) is None:
                devices[pipe.device] = []
            devices[pipe.device].append((id, pipe.name))
            ids.append(id)

        page = """
<html>
    <head>
        <title>Data Hub</title>
        <script>
            function command(name, id_array) {
                for (const id of id_array){
                    var req = new XMLHttpRequest();
                    req.open("COMMAND", '/'+name+'?id='+id, true);
                    req.send();
                    console.log('sent '+name+' to '+id);
                }
            }
        </script>
    </head>
"""

        page += """
            <body><h1>Stream Selection</h1>
            <button type="button" onclick="command('start', {all_ids})" value="startval">Start All</button>
            <button type="button" onclick="command('stop', {all_ids})" value="stopval">Stop All</button>
        """.format(all_ids=ids)

        # TODO: device-specific and infividual stream toggles not implemented yet.
        # device-specific buttons
        device_buttons = """
            <button type="button" onclick="command('start', {device_ids})" value="Start">Start</button>
            <button type="button" onclick="command('stop', {device_ids})" value="Stop">Stop</button>
        """

        # individual stream buttons
        link_buttons = """
            <button type="button" onclick="command('start', {link_id})" value="Start"></button>
            <button type="button" onclick="command('stop', {link_id})" value="Stop"></button>
        """

        # List all stream links under their host device names
        for device in devices.keys():
            page += "<p>{}</p>".format(device)
            page += "<ul>"
            for id, name in devices[device]:
                page += "<li><a href='/stream?id={}'>{}</a></li>".format(id, name)
            page += "</ul><br>"

        page += "</body></html>"
        return page


class Handler(WorkerNode):
    """
    Worker node for the Server
    Handles requests sent by Streamers and Browser connections
    """
    def __init__(self):
        super().__init__()
        self.streaming = False  # whether stream is activated
        self.initialized = False   # whether the INIT method has been called yet

        self.start_time = 0  # time stream started

    def HANDLE(self, request, threaded=True):
        """
        Overwrites default method to handle incoming requests
        If the ID of a request does not match this worker ID or is not found
            (and it wasn't sent from a data-collection client, indicated by the user-agent header),
            send the socket back to the host process to be handled
        """
        ID = request.queries.get('id')

        # ID matches this worker or the request comes from a data-collection client
        if ID == self.id or request.header.get('user-agent') == 'STREAMER':
            super().HANDLE(request, threaded=threaded)  # handle the request

        else:  # ID doesn't match or is not found, and not from a data-collection client
            #self.debug("{} Received different ID. Sending back to host".format(self.name))
            self.transfer_socket(self.pipe, request.origin, request)

    def GET(self, request):
        """
        Handles GET request from clients
        Should be extended/overwritten in derived classes
        """
        pass

    def INIT(self, request):
        """
        Handles INIT request from client
        Should be called once at session start
        Extended in derived classes
        """
        pass

    def INGEST(self, request):
        """
        Overwritten in derived classes.
        Parses the content of the request.
        Usually stores raw content and processed content in DataBuffers.
        """
        pass

    def COMMAND(self, request):
        """ Handles POST requests """
        if request.path.endswith('/start'):
            self.streaming = True
            data_socket = self.sockets[self.source_id]  # get dat-source socket
            req = HTTPRequest()  # new request
            req.add_request('START')  # call START method on client
            self.send(req, data_socket)

        elif request.path.endswith('/stop'):
            self.streaming = False
            data_socket = self.sockets[self.source_id]  # get dat-source socket
            req = HTTPRequest()  # new request
            req.add_request('STOP')  # call STOP method on client
            self.send(req, data_socket)

        else:
            self.debug("Command (path) not recognized: {}".format(request.path), 2)

        # success response
        response = HTTPResponse(204)
        self.send(response, request.origin)

    def not_active(self, request):
        """
        Send response for a stream which has been temporarily stopped.
        """

        html = """
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>{name}</title>
            </head>
            <body>
                <h1>{name} is not active.</h1>
                <p><a href='/index.html'>Back</a></p>
            </body>
            </html>
        """.format(name=self.name)

        response = HTTPRequest()
        response.add_response(200)
        response.add_header('content-type', 'text/html')
        response.add_content(html)
        self.send(response, request.origin)

    def time(self):
        """ Get time passed since the stream started """
        return time.time() - self.start_time


class GraphStream(Base):
    """
    Used to format data to be send to a browser with a Bokeh plot
    <layout> is a Bokeh layout object.
    """
    def __init__(self, layout):
        self.layout = layout

    def stream_page(self):
        """ Returns the response for the plot page """
        response = HTTPRequest()
        response.add_response(200)
        response.add_header('content-type', 'text/html')

        with open(PAGES_PATH+'/plot_page.html', 'r') as file:
            html = file.read()
        response.add_content(html)  # send initial page html
        return response

    def plot_json(self):
        """
        Returns response with full JSON of serialized plot object to be displayed in HTML.
        This is before any data is updated - it's just the basic plot layout.
        """
        response = HTTPResponse(200)
        response.add_header('content-type', 'application/json')
        response.add_content(json.dumps(json_item(self.layout)))  # send plot JSON
        return response

    def update_json(self, buffer, event):
        """
        Returns a response constructed from the data in the given buffer.
        Assumes the buffer read() method retrieves the appropriate data.
            (i.e. whether the data is meant to be appended to a plot or replace it)
        <buffer> is the data buffer from which to read.
        <event> is the event object needed to read from the buffer.
            - Obtained from buffer.get_read_lock()
        """
        data = buffer.read(event, block=False)  # read most recent data from the buffer
        if data is not None:  # new data
            # if data is str, assume it's already in JSON format
            if type(data) != str:
                data = json.dumps(data)  # convert to json
            response = HTTPResponse(200)
            response.add_header('content-type', 'application/json')
            response.add_header('Cache-Control', 'no-store')  # don't store old data or it will try to write it again when 304 code is received.
            response.add_content(data)
        else:  # no new data
            response = HTTPResponse(304)  # send 'not modified' response
        return response
