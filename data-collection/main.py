# System imports
import time
import threading
import picamera
import sys
import os
import os.path
import subprocess
import requests
import json
from datetime import datetime
from queue import Queue

# Audio imports
from audio_collecter import AudioCollecter
from audio_converter import AudioConverter
from audio_streamer import AudioStreamer

# Sense HAT imports
from sense_stream import SenseStream

# Video imports
from pi_video_server import VideoStream

# Utility imports
from utils import Utils

# Load the system configuration file
CONFIG = Utils().get_config()

# Remove any old pre-transfer data
Utils().clear_temporary_data()

# Initialize the audio sensor interface, converter, and streamer
audio_endpoint = 'http://%s:%d' % (CONFIG['SERVER_IP_ADDRESS'], 5515)
audio_streamer_thread = AudioStreamer(Queue(), args=(audio_endpoint,))
audio_converter_thread = AudioConverter(Queue(), args=(audio_streamer_thread,))
audio_collection_thread = AudioCollecter(Queue(), args=(audio_converter_thread,))

# Initialize the sense hat sensor interface and streamer
sense_endpoint = 'http://%s:%d' % (CONFIG['SERVER_IP_ADDRESS'], 5510)
sense_hat_stream = SenseStream(Queue(), args=(sense_endpoint,))

video_stream = VideoStream(Queue(), args=())

# Start the audio collection, conversion, and streaming 
audio_collection_thread.start()
audio_streamer_thread.start()
audio_converter_thread.start()

# Start the sense hat collection and streaming
sense_hat_stream.start()

# Initialize the video http server
video_stream.start()

Utils().sleep()