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
from queue import Queue

class AudioConverter(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.audio_streamer_thread = args[0]
        self.converted_count = 0
        self.mp3_file_format = 'mp3-segments/mp3_%d.mp3'
    
    def run(self):
        while True:
            time.sleep(0.05)
            queue_data = self.queue.get()
            if queue_data is None:   # If you send `None`, the thread will exit.
                return
            
            audio_wav_file_path = self.write_to_file(queue_data)
            audio_mp3_file_path = self.convert_to_mp3(audio_wav_file_path, queue_data['segment_number'])

            print("put in audio streamer thread queue")
            self.audio_streamer_thread.queue.put({'wav': audio_wav_file_path, 'mp3': audio_mp3_file_path})
    
    def write_to_file(self, data):
        segment_number = data['segment_number']
        frames = data['frames']
        wav_file_path = 'audio-segments/wav-segment%d.wav' % segment_number
        
        wavefile=wave.open(wav_file_path, 'wb')
        wavefile.setnchannels(2)
        wavefile.setsampwidth(2)
        wavefile.setframerate(44100)
        wavefile.writeframes(b''.join(frames))
        wavefile.close()
        
        print("Created audio segment: " + wav_file_path)
        
        return wav_file_path

    def convert_to_mp3(self, wave_file_path, segment_number):
        new_mp3_file_path = self.mp3_file_format % segment_number
        ffmpeg_cmd = 'ffmpeg -i %s %s' % (wave_file_path, new_mp3_file_path)
        ffmpeg_pid = subprocess.Popen(ffmpeg_cmd, shell=True)
        ffmpeg_pid.communicate()
        
        return new_mp3_file_path

