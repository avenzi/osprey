import sounddevice as sd

stream = sd.InputStream(channels=1)

while True:
    frames = stream.read_available
    print(frames)
    stream.read(frames)
    sd.sleep(1)
