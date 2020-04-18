import io
import socket
import struct
import time
import picamera
import subprocess
import itertools
import threading
import sys
import os
import os.path
import datetime
import pyaudio
import wave
import json
import requests
from queue import Queue

class AudioStreamer(threading.Thread):
    epoch = datetime.datetime.utcfromtimestamp(0)

    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.receive_messages = args[0]
        self.last_dash_segment_sent = 1
        self.dash_segment_format = 'audio-seg-%d.m4s'

    def run(self):
        while True:
            time.sleep(0.03)
            val = self.queue.get()
            if val is None:   # If you send `None`, the thread will exit.
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
                    # TODO: set in config file
                    requests.post('http://192.99.151.151:5582', 
                        data = mp3_file_bytes,
                        headers = custom_headers
                    )
                    print("Sent %s to data ingestion" % mp3_file_path)
                except Exception as e:
                    print(e)
                    print("Could not establish connection with data ingestion layer audio listener")
        else:
            raise Exception("Mp3 path did not exist in Audio Streamer")
    
    def remove_segment(self, mp3_path, wav_path):
        #segment_number = mp3_path[mp3_path.find('mp3_') + 4:-4]
        os.unlink(mp3_path) # delete mp3 segment
        os.unlink(wav_path) # delete wav segment
