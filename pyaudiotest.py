import sounddevice as sd
from time import sleep

stream = sd.InputStream(channels=1)

while True:
    frames = stream.read_available
    print(frames)
    out = stream.read(frames)
    print(out)
    sleep(1)
