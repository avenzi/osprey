from threading import Thread, Condition
from multiprocessing import Event
from requests import get
from io import BytesIO
import subprocess
import socket
import json
import inspect
import time
import os

import redis
import socketio

from lib import HostNode, WorkerNode, HTTPRequest, SocketHandler, Base

CONFIG_PATH = '../config/raspi_config.json'


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
    def __init__(self, retry=2, debug=0):
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
        Calls idle() on a new thread and waits for exit status.
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

    def connect(self, StreamerClass):
        """ Create socket object and try to connect it to the server, then run the Node class on a new process """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.debug("Attempting to connect {} to server".format(StreamerClass.__name__), 2)
            sock.connect((self.ip, self.port))
            sock.setblocking(True)
            self.debug("Socket Connected", 2)
        except Exception as e:
            self.throw("Failed to connect socket to server:", e)
            return False

        worker = StreamerClass()  # create an instance of this node class
        worker.device = self.device
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

        self.start_time = 0  # start time

    def send(self, request, socket_handler=None):
        """
        Overwriting WorkerNode send method
        Adds a user-agent header that identifies this request as being from a client streamer.
        """
        request.add_header('user-agent', 'STREAMER')
        super().send(request, socket_handler)

    def time(self):
        """ Get time passed since the stream started """
        return time.time() - self.start_time

    def _run(self):
        """
        Pre-extends the default method to automatically send the sign-on request
        Also runs the self._loop() method on a new thread
        """
        if not self.handler:
            self.throw("Streamer Node must have the attribute 'handler' to indicate which Handler class is to be used on the server")
            return

        req = HTTPRequest()  # new request
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
        self.start_time = time.time()

    def STOP(self, request):
        """
        Should be extended in streamers.py
        Ends the streaming process
        """
        self.streaming.clear()  # stop streaming, stopping the main execution while loop
        self.log("Stopped {}".format(self.name))


class HybridClient(HostNode):
    """
    Makes a connection to the Redis server.
    call run() to start.
    <retry> number of seconds to wait before attempting to connect to the server each time
    <debug> debug level of the client
    """
    def __init__(self, retry=2, debug=0):
        with open(CONFIG_PATH) as file:  # get config options
            self.config = json.load(file)
        self.ip = self.config.get('SERVER_IP_ADDRESS')  # ip address of server
        self.server_port = self.config.get('SERVER_PORT')
        self.redis_port = self.config.get('REDIS_PORT')  # port to connect through
        self.password = self.config.get('REDIS_PASS')

        name = self.config.get('NAME')  # display name of this Client
        super().__init__(name, auto=False)
        self.set_debug(debug)
        self.set_log_path(self.config.get('LOG_PATH'))
        self.retry = retry

    def run(self):
        """
        Overwritten from HostNode.run()
        Must be called on the main thread of a process.
        Calls idle() on a new thread and waits for exit status.
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

    def connect(self, StreamerClass):
        """ Create socket object and try to connect it to the server, then run the Node class on a new process """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        try:  # connect socket to given address
            self.debug("Attempting to connect {} to server".format(StreamerClass.__name__), 2)
            sock.connect((self.ip, self.server_port))
            sock.setblocking(True)
            self.debug("Socket Connected", 2)
        except Exception as e:
            self.throw("Failed to connect socket to server:", e)
            return False

        r = redis.Redis(host=self.ip, port=self.redis_port, password=self.password)
        try:
            if r.ping():
                self.log("Connection to Redis Database verified on {}:{}".format(self.ip, self.redis_port))
        except Exception as e:
            self.throw("Could not connect to Redis Database", e)
            return False

        worker = StreamerClass()  # create an instance of this node class
        worker.ip = self.ip
        worker.device = self.device
        worker.server_port = self.server_port
        worker.redis_port = self.redis_port
        worker.password = self.password
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
                sock.connect((self.ip, self.server_port))
                self.log("Server found.")
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
                break
            except Exception as e:  # failed to connect
                pass

        # Server was found, run on a new thread
        Thread(target=self._run, name=self.name+'-RUN', daemon=True).start()


class RedisClient(HostNode):
    """
    Makes a connection to the Redis server.
    call run() to start.
    <retry> number of seconds to wait before attempting to connect to the server each time
    <debug> debug level of the client
    """
    def __init__(self, debug=0):
        with open(CONFIG_PATH) as file:  # get config options
            self.config = json.load(file)
        self.ip = self.config.get('SERVER_IP_ADDRESS')  # ip address of server
        self.port = self.config.get('REDIS_PORT')  # port to connect through
        self.password = self.config.get('REDIS_PASS')

        name = self.config.get('NAME')  # display name of this Client
        super().__init__(name, auto=False)
        self.set_debug(debug)
        self.set_log_path(self.config.get('LOG_PATH'))

    def run(self):
        """
        Must be called on the main thread of a process.
        Blocks until exit status set (because this is the main thread)
        """
        self.log("Name: {}".format(self.name))
        self.log("Device IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.log("Server IP: {}".format(self.ip))
        super().run()

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
                    self.create_worker(member[1])  # connect this StreamerClass to the server
                else:  # not in the config file or not set to be used
                    self.log("Streamer class {} is not being used. Set it's keyword to 'Y' in {} to use".format(member[0], CONFIG_PATH))

    def create_worker(self, StreamerClass):
        """ Run the Node class on a new process """
        worker = StreamerClass()  # create an instance of this node class
        worker.ip = self.ip
        worker.device = self.device
        worker.port = self.port
        worker.password = self.password
        self.run_worker(worker)  # run the new worker node on a parallel process


class RedisStreamer(WorkerNode):
    """ To be used on a client to send requests to a remote Redis database """
    def __init__(self):
        super().__init__()
        self.streaming = Event()  # threading event flag set when actively streaming

        self.device = None
        self.ip = None
        self.port = None
        self.password = None
        self.type = None  # determined by derived class
        self.redis = None
        self.sio = None  # socketio client

        self.start_time = 0  # start time

    def get_redis(self):
        """ Connects to Redis"""
        try:
            self.redis = redis.Redis(host=self.ip, port=self.port, password=self.password)
        except Exception as e:
            self.log("Failed to connect to Redis: ".format(e))

    def time(self):
        """ Get time passed since the stream started """
        return time.time() - self.start_time

    def _run(self):
        """
        Overwrites _run method
        Runs the self._loop() method
        """
        # get connections
        self.sio = socketio.Client()
        self.sio.register_namespace(SocketCommunicator(self, '/streamers'))
        self.sio.connect('http://3.131.117.61:5000')
        self.log("Connected SocketIO Client")
        self.get_redis()

        # start main execution loop
        self._loop()

    def _loop(self):
        """
        Main execution loop for the streamer.
        Runs self.loop defined by user in derived class.
        """
        while not self.exit:  # run until application shutdown
            self.streaming.wait()  # wait until streaming
            try:
                self.loop()  # call user-defined main execution
            except Exception as e:
                self.stop()  # stop streaming
                continue  # wait to start again

    def loop(self):
        """
        Should be overwritten by derived class.
        Should not be called anywhere other than _loop()
        """
        pass

    def start(self):
        """
        Should be extended in streamers.py
        Begins the stream
        """
        if self.streaming.is_set():  # already running
            return
        self.redis.hmset('info:'+self.name, {'name':self.name, 'device':self.device, 'type':self.type})
        self.streaming.set()  # set streaming, which starts the main execution while loop
        self.log("Started {}".format(self.name))
        self.sio.emit('log', "Started Streamer {}".format(self.name), namespace='/streamers')
        self.start_time = time.time()

    def stop(self):
        """
        Should be extended in streamers.py
        Ends the streaming process
        """
        if not self.streaming.is_set():  # already stopped
            return
        self.streaming.clear()  # stop streaming, stopping the main execution while loop
        self.log("Stopped {}".format(self.name))
        self.sio.emit('log', "Stopped Streamer {}".format(self.name), namespace='/streamers')


class SocketCommunicator(socketio.ClientNamespace):
    """ All methods but begin with prefix "on_" followed by the usual socketio naming convention """
    def __init__(self, streamer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = streamer

    def on_connect(self):
        self.streamer.log("Connected to server")

    def on_response(self, msg):
        self.streamer.log(msg)

    def on_disconnect(self):
        self.streamer.log("Disconnected from server")

    def on_command(self, comm):
        if comm == 'START':
            self.streamer.start()
        elif comm == 'STOP':
            self.streamer.stop()
        else:
            self.streamer.log("Unrecognized Command: {}".format(comm))


class PicamOutput():
    """ Data Buffer class to collect data from a Picam. """
    def __init__(self):
        self.buffer = BytesIO()
        self.ready = Condition()  # lock for reading/writing frames

    def write(self, data):
        """ Write data to the buffer, adding the new frame when necessary """
        with self.ready:
            self.buffer.write(data)
            self.ready.notify_all()

    def read(self):
        """ Blocking operation to read the newest frame """
        with self.ready:
            self.ready.wait()  # wait for access to buffer
            data = self.buffer.getvalue()  # get all frames in buffer
            self.buffer.seek(0)  # move to beginning
            self.buffer.truncate()  # erase buffer
            return data


