import json
from datetime import datetime
from queue import Queue

# Import the Sensors to use on the system
# Raspberry Pi audio collection, conversion, streaming pipeline
from rpi_audio_collecter import RaspberryPiAudioCollector
from wav_to_mp3_converter import WavToMp3Converter
from audio_streamer import AudioStreamer

# Sense HAT collection and streaming for Raspberry Pi
from sense_stream import SenseStream

# Raspberry Pi Video HTTP video server
from rpi_video_stream import RaspberryPiVideoStream

# Utility imports
from utils import Utils

# Load the system configuration file
CONFIG = Utils().get_config()

# Remove any old pre-transfer data
Utils().clear_temporary_data()

# Initialize the audio collection, converting, and streaming
audio_endpoint = 'http://%s:%d' % (CONFIG['SERVER_IP_ADDRESS'], 5515)
audio_streamer_thread = AudioStreamer(Queue(), args=(audio_endpoint,))
audio_converter_thread = WavToMp3Converter(Queue(), args=(audio_streamer_thread,))
audio_collection_thread = RaspberryPiAudioCollector(Queue(), args=(audio_converter_thread,))

# Initialize the sense hat sensor interface and streamer
sense_endpoint = 'http://%s:%d' % (CONFIG['SERVER_IP_ADDRESS'], 5510)
sense_hat_stream = SenseStream(Queue(), args=(sense_endpoint,))


video_stream = RaspberryPiVideoStream(Queue(), args=())

# Start the audio collection, conversion, and streaming 
audio_collection_thread.start()
audio_streamer_thread.start()
audio_converter_thread.start()

# Start the sense hat collection and streaming
sense_hat_stream.start()

# Initialize the video http server
video_stream.start()

Utils().sleep()