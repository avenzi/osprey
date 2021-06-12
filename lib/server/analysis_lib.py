import socketio
import numpy as np

from lib.lib import Client, Namespace


class AnalyzerClient(Client):
    """
    Extends the Client class to run Streamers on the server dynamically.
    Streamer classes are not given, but rather created as needed.
    """
    def __init__(self, analyzers, config, debug):
        super().__init__(analyzers, config, debug)

        self.socket = socketio.Client()
        self.socket.register_namespace(Namespace(self, '/analyzer_client'))

    def run(self):
        """ Create workers to run on new processes """
        try:
            self.socket.connect('http://{}:{}'.format(self.config['SERVER_IP'], self.config['SERVER_PORT']))
            self.log("{} Connected to server socketIO".format(self.name))
        except:
            self.throw("{} Failed to connect to socketIO".format(self.name))
            return

        super().run()


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




