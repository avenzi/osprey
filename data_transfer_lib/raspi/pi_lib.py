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

from lib import HostNode, WorkerNode, Base

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


class Streamer(WorkerNode):
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


