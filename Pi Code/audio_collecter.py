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

class AudioCollecter(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.audio_converter_thread = args[0]
    
    def ensure_temporary_directories(self):
        if not os.path.exists('mp3-segments'):
            os.mkdir('mp3-segments')
        
        if not os.path.exists('audio-segments'):
            os.mkdir('audio-segments')

    def start_recording(self):
        form_1 = pyaudio.paInt16
        chans=2
        samp_rate = 44100
        chunk = 4096
        record_secs = 99999     #record time

        segment_duration = 1


        self.audio = pyaudio.PyAudio()

        # find the correct device index
        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        audio_device_id = -1
        print("Numdevices %d" % numdevices)
        for device_id in range(0, numdevices):
            if (self.audio.get_device_info_by_host_api_device_index(0, device_id).get('maxInputChannels')) > 0:
                device_name = self.audio.get_device_info_by_host_api_device_index(0, device_id).get('name')
                if 'GoMic' in device_name:
                    audio_device_id = device_id
                #print("Input Device id ", device_id, " - ", audio.get_device_info_by_host_api_device_index(0, device_id).get('name'))
        if audio_device_id == -1:
            return
        #setup audio input stream
        stream=self.audio.open(format = form_1,rate=samp_rate,channels=chans, input_device_index = audio_device_id, input=True, frames_per_buffer=chunk)
        print("Samson GoMic device id %d" % audio_device_id)
        print("Started Audio Recording")
        frames=[]

        start_time = time.time()
        current_time = start_time
        last_time = start_time
        segment_number = 0
        for ii in range(0,int((samp_rate/chunk)*record_secs)):
            data=stream.read(chunk,exception_on_overflow = False)

            print("read some audio data")
            current_time = time.time()
            if current_time > last_time + segment_duration:
                last_time = current_time
                segment_number = segment_number + 1
                print("Recorded audio segment %d " % segment_number)

                self.audio_converter_thread.queue.put({
                    'segment_number': segment_number,
                    'frames': frames.copy()
                })
                frames.clear()

            frames.append(data)

        print("finished recording")

        stream.stop_stream()
        stream.close()
        self.audio.terminate()

    def run(self):
        self.ensure_temporary_directories()
        self.start_recording()