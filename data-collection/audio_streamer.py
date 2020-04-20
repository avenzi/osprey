import io
import time
import threading
import os
import os.path
import datetime
import requests
from queue import Queue

class AudioStreamer(threading.Thread):
    epoch = datetime.datetime.utcfromtimestamp(0)

    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.server = args[0]

    def run(self):
        while True:
            time.sleep(0.03)
            val = self.queue.get()
            # If `None` is sent, the thread will exit.
            if val is None:
                return
            
            mp3_path = val['mp3']
            wav_path = val['wav']
            self.send_data(mp3_path)
            self.remove_segment(mp3_path, wav_path)

    def send_data(self, mp3_file_path):
        if os.path.exists(mp3_file_path):
            with open(mp3_file_path, "rb") as mp3_file:
                mp3_file_bytes = mp3_file.read()
                timestamp = str((datetime.datetime.now() - self.epoch).total_seconds() * 1000.0)
                custom_headers = {'filename': mp3_file_path, 'timestamp': timestamp}

                try:
                    requests.post(self.server, 
                        data = mp3_file_bytes,
                        headers = custom_headers
                    )
                except Exception as e:
                    pass
        else:
            raise Exception("Mp3 path did not exist in Audio Streamer")
    
    def remove_segment(self, mp3_path, wav_path):
        os.unlink(mp3_path) # delete mp3 segment
        os.unlink(wav_path) # delete wav segment
