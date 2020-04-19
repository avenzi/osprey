import time
import threading
import picamera
import sys
import os
import os.path
import subprocess
import requests
from datetime import datetime
from queue import Queue

# Audio imports
from audio_collecter import AudioCollecter
from audio_converter import AudioConverter
from audio_streamer import AudioStreamer

# Sense HAT imports
from sense_stream import SenseStream

from pi_video_server import VideoStream

def delete_old_audio_data():
    filelist = [ f for f in os.listdir('audio-segments') if f.endswith(".wav") ]
    for f in filelist:
        os.remove(os.path.join('audio-segments', f))
    
    filelist = [ f for f in os.listdir('mp3-segments') if f.endswith(".mp3") ]
    for f in filelist:
        os.remove(os.path.join('mp3-segments', f))
delete_old_audio_data()
time.sleep(1.0)

audio_streamer_thread = AudioStreamer(Queue(), args=('http://192.99.151.151:5515',)) # TODO: replace with rpi config value
audio_converter_thread = AudioConverter(Queue(), args=(audio_streamer_thread,))
audio_collection_thread = AudioCollecter(Queue(), args=(audio_converter_thread,))

sense_hat_stream = SenseStream(Queue(), args=('http://192.99.151.151:5510',)) # TODO: replace with rpi config value

video_stream = VideoStream(Queue(), args=())

audio_collection_thread.start()
audio_streamer_thread.start()
audio_converter_thread.start()

sense_hat_stream.start()

video_stream.start()

time.sleep(9999999)
