import io
import time
import subprocess
import threading
import wave
from queue import Queue

"""
Takes WAV file path as input and converts the file to MP3 using FFmpeg as a subprocess,
then passes the file paths to another thread. Requires FFmpeg installation with libmp3lame.
"""
class WavToMp3Converter(threading.Thread):
    # MP3 filepath format based on unique identifier
    mp3_file_format = "mp3-segments/mp3_%d.mp3"

    # WAV filepath format based on unique identifier
    wav_file_format = 'audio-segments/wav-segment%d.wav'

    sample_rate = 44100

    # 2 channels for stereo
    channels = 2

    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.audio_streamer_thread = args[0]
    
    def run(self):
        while True:
            time.sleep(0.05)
            queue_data = self.queue.get()
            # If you send `None`, the thread will exit
            if queue_data is None:
                return
            
            audio_wav_file_path = self.write_to_file(queue_data)
            audio_mp3_file_path = self.convert_to_mp3(audio_wav_file_path, queue_data['segment_number'])
            self.audio_streamer_thread.queue.put({'wav': audio_wav_file_path, 'mp3': audio_mp3_file_path})
    
    def write_to_file(self, data):
        segment_number = data['segment_number']
        frames = data['frames']
        wav_file_path = self.wav_file_format % segment_number
        
        wavefile=wave.open(wav_file_path, 'wb')
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(2)
        wavefile.setframerate(self.sample_rate)
        wavefile.writeframes(b''.join(frames))
        wavefile.close()
        
        return wav_file_path

    def convert_to_mp3(self, wave_file_path, segment_number):
        new_mp3_file_path = self.mp3_file_format % segment_number
        ffmpeg_cmd = 'ffmpeg -i %s %s' % (wave_file_path, new_mp3_file_path)
        ffmpeg_pid = subprocess.Popen(ffmpeg_cmd, shell=True)
        ffmpeg_pid.communicate()
        
        return new_mp3_file_path

