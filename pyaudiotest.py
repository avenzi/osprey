import sounddevice as sd
from time import sleep

def callback(indata, frames, time, status):
    print(len(indata))

stream = sd.InputStream(channels=1, callback=callback, samplerate=44100)

stream.start()

sleep(5)
stream.stop()