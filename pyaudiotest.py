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

ffmpeg_process = (
    ffmpeg
    .input('pipe:')
    .output('pipe:')
    .run_async(pipe_stdin=True, pipe_stdout=True)
)

for i in range(10):
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

    out_data = ffmpeg_process.stdout.read()
    print('ffmpeg out data:', len(out_data))
    if not out_data:
        print('no data read back from ffmpeg')
        sleep(1)
        continue
    sleep(1)

print('total in_buf:', len(in_buf.getvalue()))
print('total out_buf:', len(out_buf.getvalue()))


stream.stop()
print('stopped')

ffmpeg_process.wait()
print('finished waiting')

