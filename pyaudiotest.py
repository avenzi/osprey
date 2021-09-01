import sounddevice as sd
from time import sleep


stream = sd.InputStream(device="USB Audio Device", channels=1)
stream.start()
while True:
    frames = stream.read_available
    print(frames)
    out = stream.read(1)
    sleep(1)

'''
# working
fs=44100
duration=5
print("recording...............")

recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()
print(recording, sum(recording))
'''
