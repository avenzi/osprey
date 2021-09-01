import sounddevice as sd
from time import sleep

stream = sd.InputStream(channels=1)

while True:
    frames = stream.read_available
    print(frames)
    stream.read(frames)
    sleep(1)
