import io
import time
import threading
import os
import os.path
import pyaudio
from queue import Queue

"""
Collects segmented audio from a Samsung Go microphone through PyAudio
and passes it to another thread for processing. Requires PyAudio.
"""
class RaspberryPiAudioCollecter(threading.Thread):
    samp_rate = 44100

    # The number of bytes of data to read from the microphone before processing the chunk
    chunk_size = 4096

    # The duration of a single audio segment in seconds
    segment_duration = 1

    # The number of audio channels (2 for stereo)
    channels = 2

    # The name of the audio device to match when searching the system's audio devices
    device_name = 'GoMic' # Configured for Samsung GoMic (stereo)

    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.audio_converter_thread = args[0]
    
    # Ensures the temporary directories where the data is held for processing exist
    def ensure_temporary_directories(self):
        if not os.path.exists('mp3-segments'):
            os.mkdir('mp3-segments')
        
        if not os.path.exists('audio-segments'):
            os.mkdir('audio-segments')

    def start_recording(self):
        form_1 = pyaudio.paInt16

        self.audio = pyaudio.PyAudio()

        # Find the audio device
        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        audio_device_id = -1

        for device_id in range(0, numdevices):
            if (self.audio.get_device_info_by_host_api_device_index(0, device_id).get('maxInputChannels')) > 0:
                device_name = self.audio.get_device_info_by_host_api_device_index(0, device_id).get('name')
                if self.device_name in device_name:
                    audio_device_id = device_id
        
        if audio_device_id == -1:
            # Do not collect audio if the proper audio device cannot be found
            return
        
        # Create the audio input stream
        stream = self.audio.open(
            format=form_1,
            rate=self.samp_rate,
            channels=self.channels,
            input_device_index=audio_device_id,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        frames=[]
        start_time = time.time()
        current_time = start_time
        last_time = start_time
        segment_number = 0
        for x in range(0, int((self.samp_rate/self.chunk_size)*441000)):
            data = stream.read(self.chunk_size, exception_on_overflow=False)

            current_time = time.time()
            if current_time > last_time + self.segment_duration:
                last_time = current_time
                segment_number = segment_number + 1

                self.audio_converter_thread.queue.put({
                    'segment_number': segment_number,
                    'frames': frames.copy()
                })
                frames.clear()
            frames.append(data)

        stream.stop_stream()
        stream.close()
        self.audio.terminate()

    def run(self):
        self.ensure_temporary_directories()
        self.start_recording()