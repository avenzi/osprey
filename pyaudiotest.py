import sounddevice as sd
import soundfile as sf
from lib.raspi.pi_lib import BytesOutput2
from io import BytesIO
from time import sleep

buf = BytesOutput2()
samplerate = 44100
channels = 1

file = sf.SoundFile(buf, mode='w', samplerate=samplerate, channels=channels, format='WAV')


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    file.write(indata)


stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback)

stream.start()
print('started')

for i in range(10):
    data = buf.read()
    print(len(data))
    sleep(1)


stream.stop()
print('stopped')

