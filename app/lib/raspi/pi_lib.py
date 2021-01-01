from threading import Thread
from multiprocessing import Event
from requests import get
import subprocess
import socket
import json
import inspect
import time
import os

from ..lib import HostNode, WorkerNode, Request, SocketHandler

CONFIG_PATH = 'lib/raspi/config.json'


def configure_port(dev_path):
    """
    Used for data collection devices which rely on the Pi's internal timer to time-stamp data.
    Sets the internal buffer for the given VCP port to 1ms-latency in order to avoid data chunking.
    This setting gets reset when the device is disconnected or the Pi is power cycled,
        so it needs to be run each time the client begins streaming
    """
    device = dev_path[dev_path.index('tty'):]
    filepath = "/sys/bus/usb-serial/devices/{}/latency_timer".format(device)
    if os.path.exists(filepath):
        subprocess.Popen("echo 1 | sudo tee {}".format(filepath), shell=True, stdout=subprocess.PIPE)
        return True
    else:
        print("Could not configure serial device - path doesn't exist")
        return False


class Client(HostNode):
    """
    Makes a connection to the server.
    Handler classes are used to handle individual requests.
    call run() to start.
    <retry> number of seconds to wait before attempting to connect to the server each time
    <debug> debug level of the client
    """
    def __init__(self, retry=5, debug=0):
        with open(CONFIG_PATH) as file:  # get config options
            self.config = json.load(file)
        self.ip = self.config.get('SERVER_IP_ADDRESS')  # ip address of server
        self.port = self.config.get('PORT')  # port to connect through

        name = self.config.get('NAME')  # display name of this Client
        super().__init__(name, auto=False)
        self.set_debug(debug)
        self.set_log_path(self.config.get('LOG_PATH'))
        self.retry = retry

    def run(self):
        """
        Overwritten from HostNode.run()
        Must be called on the main thread of a process.
        Calls idle() and _run() on a new thread and waits for exit status.
        Blocks until exit status set (because this is the main thread)
        """
        self.log("Name: {}".format(self.name))
        self.log("Device IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.log("Server IP: {}".format(self.ip))

        # search for a server to connect to, call _run() when found.
        Thread(target=self.idle, name=self.name+'-IDLE', daemon=True).start()
        self.run_exit_trigger(block=True)  # block main thread until exit

    def _run(self):
        """
        Called by self.run() on a new thread.
        Creates one instance of each handler type from collection_lib
            For each handler class, listens for new connections then starts them on their own thread.
        """
        # get selected handler classes
        from . import streamers
        members = inspect.getmembers(streamers, inspect.isclass)  # all classes [(name, class), ]
        for member in members:
            if member[1].__module__.split('.')[-1] == 'streamers':  # imported from the streamers.py file
                config = self.config['STREAMERS'].get(member[0])  # configuration of whether this class is to be used or not
                if config and config.upper() == 'Y':  # this class is in the config file and set to be used
                    self.connect(member[1])  # connect this StreamerClass to the server
                else:  # not in the config file or not set to be used
                    self.log("Streamer class {} is not being used. Set it's keyword to 'Y' in {} to use".format(member[0], CONFIG_PATH))

    def connect(self, NodeClass):
        """ Create socket object and try to connect it to the server, then run the Node class on a new process """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.debug("Attempting to connect {} to server".format(NodeClass.__name__), 2)
            sock.connect((self.ip, self.port))
            sock.setblocking(True)
            self.debug("Socket Connected", 2)
        except Exception as e:
            self.throw("Failed to connect socket to server:", e)
            return False

        worker = NodeClass()  # create an instance of this node class
        worker.set_source(sock)  # set this socket as a data-source socket for the client
        self.run_worker(worker)  # run the new worker node on a parallel process

    def idle(self):
        """
        Attempts to connect a dummy socket to the server.
            If no server found, waits some amount of time then tries again.
            Once found, closes the dummy socket and calls self._run()
        """
        self.log("Waiting to find server...")
        while True:  # try to connect every interval
            time.sleep(self.retry)  # wait to try again
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
            try:  # connect socket to given address
                sock.connect((self.ip, self.port))
                self.log("Server found.")
                # This code would be used if we wanted to use the dummy socket for something.
                #  Instead, we just immediately close it.
                # new_handler = SocketHandler(sock, self, name="DummySocket")  # wrap raw socket in socket handler
                # sock_id = self.add_socket(new_handler)  # add to socket index
                # self.sockets[sock_id].run()  # run the new socket handler
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
                break
            except Exception as e:  # failed to connect
                pass

        # Server was found, run on a new thread
        Thread(target=self._run, name=self.name+'-RUN', daemon=True).start()


class Streamer(WorkerNode):
    """
    To be used on a client to send requests to the Handler
    """
    def __init__(self):
        super().__init__()
        self.handler = None  # class name of the handler to use on the server
        self.streaming = Event()  # threading event flag set when actively streaming
        self.time = 0  # start time

    def send(self, request, socket_handler=None):
        """
        Overwriting WorkerNone send method
        Adds a user-agent header that identifies this request as being from a client streamer.
        """
        request.add_header('user-agent', 'STREAMER')
        super().send(request, socket_handler)

    def _run(self):
        """
        Pre-extends the default method to automatically send the sign-on request
        Also runs the self._loop() method on a new thread
        """
        if not self.handler:
            self.throw("Streamer Node must have the attribute 'handler' to indicate which Handler class is to be used on the server")
            return

        req = Request()  # new request
        req.add_request('SIGN_ON')
        req.add_header('name', self.name)  # name of the class to be displayed
        req.add_header('device', self.device)  # name of host Node
        req.add_header('class', self.handler)  # class name of the handler to use at the other end
        self.send(req, self.sockets[self.source_id])

        # start main execution loop
        Thread(target=self._loop, name='{}-LOOP'.format(self.name), daemon=True).start()
        super()._run()  # continue _run method. Runs the sockets on this worker.

    def _loop(self):
        """
        Main execution loop for the streamer.
        Runs self.loop defined by user in derived class.
        """
        while not self.exit:  # run until application shutdown
            self.streaming.wait()  # wait until streaming
            self.loop()  # call user-defined main execution

    def loop(self):
        """
        Should be overwritten by derived class.
        Should not be called anywhere other than _loop()
        """
        pass

    def START(self, request):
        """
        Should be extended in streamers.py
        Begins the streaming process, using self.send() to send each data packet.
        """
        if self.streaming.is_set():
            self.log("{} received START request, but it is already running".format(self.name))
            return
        self.streaming.set()  # set streaming, which starts the main execution while loop
        self.log("Started {}".format(self.name))
        self.time = time.time()

    def STOP(self, request):
        """
        Should be extended in streamers.py
        Ends the streaming process
        """
        self.streaming.clear()  # stop streaming, stopping the main execution while loop
        self.log("Stopped {}".format(self.name))

