import os
import sys
import time
import subprocess
import threading

from app import app, mysql
from queue import Queue


class Program(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.filename = args[1]
        self.user_id = args[2]
        self.name = self.filename

    def run(self):
        # Creating a child process for a selected python file
        process = subprocess.Popen(['python3', os.path.join(app.config['UPLOADS_FOLDER'], self.filename)])

        while True:
            time.sleep(0.075)
            # If process has ended or had an error, ensure Status is set to 0 (not running) in Algorithm table, and kill the thread
            if process.poll() is not None:
                print("Process Ended...")

                with app.app_context():
                    sql = """
                        UPDATE Algorithm
                        SET Status = 0
                        WHERE UserId = %s AND Path = %s;
                    """
                    database_cursor = mysql.connection.cursor()
                    database_cursor.execute(sql, (self.user_id, self.filename.split('.')[0]))
                    mysql.connection.commit()

                sys.exit()