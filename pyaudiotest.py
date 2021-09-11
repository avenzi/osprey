import ffmpeg
import sounddevice as sd
from lib.raspi.pi_lib import BytesOutput2
from io import BytesIO
from time import sleep
from threading import Thread
import os

in_buf = BytesOutput2()
out_buf = BytesIO()
samplerate = 44100
channels = 1
signal = False

ffmpeg_process = (
    ffmpeg
    .input('pipe:', format='f32le', ac='1')  # SoundDevice outputs Float-32, little endian by default.
    .output('pipe:', format='adts')  # AAC format
    #.output('test.aac')
    #.global_args("-loglevel", "quiet")
    .run_async(pipe_stdin=True, pipe_stdout=True)
)

# write raw audio to ffmpeg process
def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    ffmpeg_process.stdin.write(indata)


stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback)

# read from ffmpeg
def read():
    while not signal:
        out_data = ffmpeg_process.stdout.read(8*1024)
        print('read from ffmpeg:', len(out_data))
        if not out_data:
            print('no data read back from ffmpeg')
            sleep(1)
            continue
        out_buf.write(out_data)
        sleep(0.1)
    print('ended read thread')


stream.start()
print('started')

Thread(target=read).start()

sleep(10)

stream.stop()
print('stopped')

signal = True
print('set signal')

print('total out_buf:', len(out_buf.getvalue()))


