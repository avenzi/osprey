import sounddevice as sd
import soundfile as sf
from lib.raspi.pi_lib import BytesOutput
from io import BytesIO
import ffmpeg
from time import sleep


import sounddevice as sd
import soundfile as sf
from lib.raspi.pi_lib import BytesOutput2
from io import BytesIO
from time import sleep

in_buf = BytesIO()
out_buf = BytesIO()
samplerate = 44100
channels = 1

file = sf.SoundFile(in_buf, mode='w', samplerate=samplerate, channels=channels, format='WAV')


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    file.write(indata)


stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback)

stream.start()
print('started')


in_file = ffmpeg.input(in_buf)
out_file = ffmpeg.output(out_buf)
(
    ffmpeg
    .output(out_file)
    .run()
)

for i in range(10):
    sleep(1)
    print(len(out_buf.getvalue()))

print('in:', len(in_buf.getvalue()))
print('out:', len(out_buf.getvalue()))


stream.stop()
print('stopped')

