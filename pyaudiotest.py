import sounddevice as sd

stream = sd.Stream(channels=1)

while True:
    frames = stream.read_available
    print(frames)
    stream.read(frames)
    sd.sleep(1)
