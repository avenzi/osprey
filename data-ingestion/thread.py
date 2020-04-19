import threading
from queue import Queue

class Thread(threading.Thread):
    def __init__(self, data):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = Queue()
        self.daemon = True
        self.data = data
        self.http_server = data['http_server'] if 'http_server' in data else None
        self.runnable_instance = data['runnable_instance'] if 'runnable_instance' in data else None
    
    def run(self):
        if self.http_server:
            self.http_server.serve_forever()
        elif self.runnable_instance:
            self.runnable_instance.run(self.data)