import numpy as np


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


def validate_input(message, expecting, case=False):
    """
    Rudimentary user input validation
    <message> input message to be displayed
    <expecting> List of expected strings
    <case> Bool, whether case sensitive. If False, answer is always converted to lower case.
    """
    # TODO: add regex option to the <expecting> argument
    if not case:  # not case sensitive
        expecting = [s.lower() for s in expecting]

    while True:
        ans = input(message).strip()
        if not case:
            ans = ans.lower()
        if ans in expecting:  # valid
            break
        else:  # invalid
            print("Invalid input. Expecting: {}".format(expecting))

    return ans