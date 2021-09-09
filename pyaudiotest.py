import sounddevice as sd
import soundfile as sf
from lib.raspi.pi_lib import BytesOutput
from io import BytesIO
import ffmpeg
from time import sleep
from picamera import PiCamera, PiVideoFrameType


camera = PiCamera(resolution='200x200', framerate=20)
camera.rotation = 180
sps = PiVideoFrameType.sps_header
infile = BytesIO()
outfile = BytesIO()


# start recording
camera.start_recording(infile,
                            format='h264', quality=25, profile='constrained', level='4.2',
                            intra_period=camera.framerate[0], intra_refresh='both', inline_headers=True, sps_timing=True
                            )
sleep(2)  # let camera warm up for a sec. Does weird stuff otherwise.


in_file = ffmpeg.input(infile)
out_file = ffmpeg.output(outfile)
(
    ffmpeg
    .drawbox(50, 50, 120, 120, color='red', thickness=5)
    .output(out_file)
    .run()
)

for i in range(10):
    sleep(1)
    print(len(outfile.getvalue()))

print('in:', len(infile.getvalue()))
print('out:', len(outfile.getvalue()))

