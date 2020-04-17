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

# Sense stream imports
from sense_stream import SenseStream

# TODO: move into a utility class
def delete_old_audio_data():
    filelist = [ f for f in os.listdir('audio-segments') if f.endswith(".wav") ]
    for f in filelist:
        os.remove(os.path.join('audio-segments', f))
    
    filelist = [ f for f in os.listdir('mp3-segments') if f.endswith(".mp3") ]
    for f in filelist:
        os.remove(os.path.join('mp3-segments', f))
delete_old_audio_data()
time.sleep(1.0)


# Define server and log files
server = "http://51.161.8.254:5568" # TODO: get from rpi config
log = open("/home/pi/Desktop/PiCode/Logs/" + str(datetime.now()), "w+")

audio_streamer_thread = AudioStreamer(Queue(), args=(True,))    
audio_converter_thread = AudioConverter(Queue(), args=(audio_streamer_thread,))
audio_collection_thread = AudioCollecter(Queue(), args=(audio_converter_thread,))

audio_collection_thread.start()
audio_streamer_thread.start()
audio_converter_thread.start()

time.sleep(9999999)

# continuously attempt to start connection
while True:
    try:
        sense_stream.stream(server, log)
        
    except Exception as e:
        # Write to log file
        print("Exception caught: ", e, file = log)
        time.sleep(.5)
        
log.close()
