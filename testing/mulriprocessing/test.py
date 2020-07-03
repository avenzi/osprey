import multiprocessing
from multiprocessing import Process
import time

class Server:
    def __init__(self):
        self.val = 0

    def inc(self):
        self.val += 1
        print(self.val)

    def run(self):
        for i in range(5):
            p = Process(target=self.inc, daemon=True, name="P-{}".format(i))
            p.start()
            print("started", i)


var = 0
def f(var):
    var += 1
    print(var)


if __name__ == "__main__":
    for i in range(5):
        p = Process(target=f, daemon=True, args=(var,), name="P-{}".format(i))
        p.start()
