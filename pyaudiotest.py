import sounddevice as sd
from time import sleep


def callback(indata, frames, time, status):
    print(len(indata))

stream = sd.InputStream(channels=1, callback=callback)

with stream:
    sd.sleep(20000)

'''
# working
fs=44100
duration=5
print("recording...............")

recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()
print(recording, sum(recording))
'''
