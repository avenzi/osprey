import numpy as np
import inspect

from lib import Client

CONFIG_PATH = '../config/analyzer_config.json'


class AnalyzerClient(Client):
    """ Extends the Client class to run Streamers on the server """
    def _run(self):
        """
        Called by self.run() on a new thread.
        Create workers to run on new processes
        """
        from . import analyzers
        members = inspect.getmembers(analyzers, inspect.isclass)  # all classes [(name, class), ]
        for member in members:
            if member[1].__module__.split('.')[-1] == 'analyzers':  # imported from the streamers.py file
                self.run_worker(member[1])


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




