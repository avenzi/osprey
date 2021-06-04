import socketio
import numpy as np
import inspect

from lib.lib import Client, Namespace

CONFIG_PATH = 'config/server_streamer_config.json'


class AnalyzerClient(Client):
    """
    Extends the Client class to run Streamers on the server

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.socket = socketio.Client()
        self.socket.register_namespace(AnalyzerClientNamespace(self, '/analyzer_client'))

        # dict of worker classes (not instances) associated with each target stream name
        self.analyzer_classes = {}  # {target_stream_name: [analyzer_class1, analyzer_class2, ...], ...}

        # list of IDs from remote streamers that have analyzers already deployed.
        self.active_analyzers = {}  # {target_stream_id: [analyzer_class1, analyzer_class2, ...], ...}

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
            if member[1].__module__.split('.')[-1] == 'analyzers':  # imported from the analyzers.py file
                worker_class = member[1]

                # list of classes meant to analyze that target streamer name
                analyzer_class_list = self.analyzer_classes.get(worker_class.target_name)

                # add this class to the list
                if analyzer_class_list is None:
                    self.analyzer_classes[worker_class.target_name] = [worker_class]
                else:
                    self.analyzer_classes[worker_class.target_name].append(worker_class)

    def create_analyzer(self, info):
        """ Create analyzer to analyze stream with given ID """
        streamer_name = info['name']
        streamer_id = info['id']

        # get list of Analyzer classes made for this streamer name
        classes = self.analyzer_classes.get(streamer_name)

        # if no classes exist to analyze this streamer name
        if not classes:
            return

        # get active analyzer classes for this streamer ID
        active_classes = self.active_analyzers.get(streamer_id, [])
        if not active_classes:
            self.active_analyzers[streamer_id] = []

        for AnalyzerClass in classes:
            # if this class isn't already bound to this Streamer ID
            if AnalyzerClass not in active_classes:
                self.active_analyzers[streamer_id].append(AnalyzerClass)  # add to the list
                self.log("Analyzer {} bound to incoming stream: {} identified".format(AnalyzerClass.__name__, streamer_name))
                worker = AnalyzerClass(self.config)

                # give it the streamer ID
                worker.target_id = streamer_id

                # override it's own ID with the prefixed streamer ID
                worker.id = worker.name + ':' + streamer_id
                self.run_worker(worker)


class AnalyzerClientNamespace(Namespace):
    def on_init(self, info):
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




