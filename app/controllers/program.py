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
        self.user_id = args[2]
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):

        # Passing user_id into a tmp file to be accessed by boilerplate and deleted
        f = open("app/static/tempfiles/tmp.txt", "w")
        f.write(str(self.user_id))
        f.close()

        # Creating a child process for a selected python file. If sending data to the child process' stdin, you must create the Popen object with stdin=PIPE.
        # Similarly, to get anything other than None in the result tuple, you need to use stdout=PIPE and/or stderr=PIPE
        process = subprocess.Popen(['python3', os.path.join(app.config['UPLOADS_FOLDER'], self.filename)], stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while self.is_running:
            time.sleep(0.075)
            print("Process Running...")
            if process.poll() is not None:
                print("Process Ended, Exiting Loop...")

                # Remove tmp file if it exists
                if os.path.exists("app/static/tempfiles/tmp.txt"):
                    os.remove("app/static/tempfiles/tmp.txt")
                else:
                    print("The file does not exist")

                sys.exit()
        
        # Remove tmp file if it exists
        if os.path.exists("app/static/tempfiles/tmp.txt"):
            os.remove("app/static/tempfiles/tmp.txt")
        else:
            print("The file does not exist")

        print("Exiting Loop Immediately")
        process.kill()
        sys.exit()