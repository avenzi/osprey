import os
import sys
import time
import subprocess
import threading

from app import app
from queue import Queue


class Program(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.filename = args[1]
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        print("Running...")

        # Creating a child process for a selected python file. If sending data to the child process' stdin, you must create the Popen object with stdin=PIPE.
        # Similarly, to get anything other than None in the result tuple, you need to use stdout=PIPE and/or stderr=PIPE
        process = subprocess.Popen(['python3', os.path.join(app.config['UPLOADS_FOLDER'], self.filename)], 
            bufsize=0, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while self.is_running:
            time.sleep(0.075)
            if process.poll() is not None:
                sys.exit()
        sys.exit()

        # while (self.is_running) and (process.poll() is None):
        #     time.sleep(0.075)

        #     print("In while loop")

        #     # The dataString is contains all temperatureData, audioData, and eventLogData, delimited by /
        #     dataString = (temperatureData.roomTemperature + "/" + temperatureData.skinTemperatureSub1 + "/" + temperatureData.skinTemperatureSub2 + "/" + 
        #         temperatureData.status + "/" + temperatureData.date + "/" + audioData.decibels + "/" + audioData.status + "/" + audioData.date + "/" + 
        #             eventLogData.temperatureStatus + "/" + eventLogData.audioStatus)

        #     process.stdin.write(dataString.encode())

        # sys.exit()