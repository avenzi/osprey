from threading import Thread
from requests import get
import socket
import json
import inspect
import time

from ..lib import HostNode, WorkerNode, Request

CONFIG_PATH = 'lib/raspi/config.json'


class Client(HostNode):
    """
    Makes a connection to the server.
    HandlerClass is used to handle individual requests.
    call run() to start.
    """
    def __init__(self, ip, port, name, debug=0):
        super().__init__(name, auto=True)
        self.set_debug(1)

        self.ip = ip  # server ip address to connect to
        self.port = port  # server port to connect through

    def run(self):
        """
        Main entry point.
        Must be called on the main thread of a process.
        Calls _run on a new thread and waits for exit status.
        Blocks until exit status set.
        """
        Thread(target=self._run, name=self.name+'-RUN', daemon=True).start()
        self.run_exit_trigger(block=True)  # block main thread until exit

    def _run(self):
        """
        Should be called on a new thread.
        Creates one instance of each handler type from collection_lib
        For each handler class, listens for new connections then starts them on their own thread.
        """
        self.log("Name: {}".format(self.name))
        self.log("Device IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.log("Server IP: {}".format(self.ip))

        with open(CONFIG_PATH) as file:
            config = json.load(file)

        # get selected handler classes
        from . import streamers
        members = inspect.getmembers(streamers, inspect.isclass)  # all classes [(name, class), ]
        for member in members:
            if member[1].__module__.split('.')[-1] == 'streamers' and config['HANDLERS'][member[0]].upper() == 'Y':  # class selected in config file
                self.connect(member[1])  # connect this HandlerClass to the server

    def connect(self, NodeClass):
        """ Create socket object and try to connect it to the server, then run the Node class on a new process """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.debug("Attempting to connect to server", 2)
            sock.connect((self.ip, self.port))
            sock.setblocking(True)
            self.debug("Socket Connected", 2)
        except Exception as e:
            self.throw("Failed to connect socket to server:", e)
            return False

        worker = NodeClass()  # create an instance of this node class
        worker.set_source(sock)  # set this socket as a data-source socket for the client
        self.run_worker(worker)  # run the new worker node on a parallel process


class Streamer(WorkerNode):
    """
    To be used on a client to send requests to the Handler
    """
    def __init__(self):
        super().__init__()
        self.handler = None  # class name of the handler to use on the server
        self.streaming = False  # flag set when actively streaming
        self.time = 0  # start time

    def send(self, request, socket_handler):
        """
        Overwriting default send method
        Adds a user-agent header that identifies this request as being from a client streamer.
        """
        request.add_header('user-agent', 'STREAMER')
        super().send(request, socket_handler)

    def _run(self):
        """ Pre-extends the default method to automatically send the sign-on request """
        if not self.handler:
            self.throw("Streamer Node must have the attribute 'handler' to indicate which Handler class is to be used on the server")
            return

        req = Request()  # new request
        req.add_request('SIGN_ON')
        req.add_header('name', self.name)  # name of the class to be displayed
        req.add_header('device', self.device)  # name of host Node
        req.add_header('class', self.handler)  # class name of the handler to use at the other end
        self.send(req, self.sockets[self.source_id])

        super()._run()  # continue _run method. Runs the sockets on this worker.

    def START(self, request):
        """
        Should be extended in streamers.py
        Begins the streaming process, using self.send() to send each data packet.
        """
        if self.streaming:
            self.log("{} received START request, but it is already running".format(self.name))
            return
        self.streaming = True
        self.log("Started {}".format(self.name))
        self.time = time.time()

    def STOP(self, request):
        """
        Should be extended in streamers.py
        Ends the streaming process
        """
        self.streaming = False
        self.log("Stopped {} at {}".format(self.name, self.get_date()))
