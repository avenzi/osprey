import socketio
import numpy as np
import inspect

from lib import Client

CONFIG_PATH = '../config/server_streamer_config.json'


class AnalyzerClient(Client):
    """ Extends the Client class to run Streamers on the server """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.socket = socketio.Client()
        self.socket.register_namespace(SocketCommunicator(self, '/analyzer_client'))

        # dict of worker classes (not instances)
        self.analyzer_classes = {}  # {target_stream_name: analyzer_class, ...}

        # list of IDs from remote streamers that have analyzers already deployed.
        self.active_analyzers = []

    def _run(self):
        """
        Called by self.run() on a new thread.
        Create workers to run on new processes
        """
        self.socket.connect('http://{}:{}'.format(self.config['SERVER_IP'], self.config['SERVER_PORT']))
        self.log("{} Connected to server socketIO".format(self.name))

        from . import analyzers
        members = inspect.getmembers(analyzers, inspect.isclass)  # all classes [(name, class), ]
        for member in members:
            if member[1].__module__.split('.')[-1] == 'analyzers':  # imported from the streamers.py file
                worker_class = member[1]
                self.analyzer_classes[worker_class.target_name] = worker_class

    def create_analyzer(self, info):
        """ Create analyzer to analyze stream with given ID """
        streamer_name = info['name']
        streamer_id = info['id']

        # get an Analyzer class made for this streamer name
        AnalyzerClass = self.analyzer_classes.get(streamer_name)

        # if this Analyzer class exists and a streamer with this ID isn't already being analyzed
        if AnalyzerClass and streamer_id not in self.active_analyzers:
            self.active_analyzers.append(streamer_id)  # add to list of streamer IDs being analyzed
            self.log("Analyzer {} bound to incoming stream: {} identified".format(AnalyzerClass.__name__, stream_name))
            worker = AnalyzerClass(self.config)
            worker.target_id = info['id']  # give it the streamer id
            self.run_worker(worker)


class SocketCommunicator(socketio.ClientNamespace):
    """ All methods must begin with prefix "on_" followed by socketIO message name"""
    def __init__(self, streamer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = streamer

    def on_connect(self):
        self.emit('log', '{} connected to server'.format(self.streamer.name))

    def on_disconnect(self):
        #self.streamer.log("{} disconnected from socketIO server".format(self.streamer.name))
        pass

    def on_ready(self, info):
        """ Passed info from a recently connected stream """
        self.streamer.create_analyzer(info)


class MovingAverage:
    """
    Keeps a moving average using a ring buffer
    <size> Size of the moving average buffer
    """
    def __init__(self, size):
        self.size = size  # max size
        self.length = 0  # current size

        self.array = []  # value array
        self.head = 0  # next index at which to place a value

        self.value = 0  # current average

    def calculate(self):
        """ calculate the current average """
        self.value = np.average(self.array)

    def add(self, val):
        """ Add a value to the moving average """
        if self.length < self.size:  # not full
            self.array.append(val)
            self.length += 1
        else:  # full
            self.array[self.head] = val
        self.head = (self.head + 1) % self.size
        self.calculate()
        return self.value




