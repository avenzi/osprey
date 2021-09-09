import ffmpeg
import sounddevice as sd
import soundfile as sf
from lib.raspi.pi_lib import BytesOutput2
from io import BytesIO
from time import sleep
from threading import Thread

in_buf = BytesOutput2()
out_buf = BytesIO()
samplerate = 44100
channels = 1
signal = False

file = sf.SoundFile(in_buf, mode='w', samplerate=samplerate, channels=channels, format='WAV')

# write to buffer
def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    file.write(indata)


stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback)

ffmpeg_process = (
    ffmpeg
    .input('pipe:', format='wav', ac='1')
    .output('pipe:', format='wav', ac=1, ar=44100)
    #.global_args("-loglevel")
    .run_async(pipe_stdin=True, pipe_stdout=True)
)

# write to ffmpeg
def write():
    while not signal:
        in_data = in_buf.read()
        print('in buf data: ', len(in_data))
        if not in_data:
            print('no data read from in_buf')
            sleep(1)
            continue

        written_data = ffmpeg_process.stdin.write(in_data)
        print('written data:', len(in_data))
        if not written_data:
            print('no data written')
            sleep(1)
            continue

        sleep(1)
    print('ended write thread')
Thread(target=write).start()


# read from ffmpeg
def read():
    while not signal:
        print('gonna read')
        out_data = ffmpeg_process.stdout.read()
        print('ffmpeg out data:', len(out_data))
        if not out_data:
            print('no data read back from ffmpeg')
            sleep(1)
            continue

        out_buf.write(out_data)
        sleep(1)
    print('ended read thread')
Thread(target=read).start()


stream.start()
print('started')

sleep(10)

stream.stop()
print('stopped')

signal = True
print('set signal')

print('total out_buf:', len(out_buf.getvalue()))


