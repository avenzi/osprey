import sounddevice as sd
from time import sleep

stream = sd.InputStream(channels=1)
stream.start()
while True:
    frames = stream.read_available
    print(frames)
    out = stream.read(frames)
    sleep(1)
