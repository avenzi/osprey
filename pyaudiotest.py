import pyaudio

fmt = pyaudio.paInt16  # 16-bit resolution
sample_rate = 44100  # 44.1kHz sampling rate
chunk_size = 4096  # 2^12 samples for buffer
record_secs = 3  # seconds to record
dev_index = 2  # device index found by p.get_device_info_by_index(ii)

audio = pyaudio.PyAudio()  # create pyaudio instantiation

# create pyaudio streams
stream = audio.open(format=fmt, rate=sample_rate, channels=1,
                    input_device_index=dev_index, input=True,
                    frames_per_buffer=chunk_size)
print("recording")
frames = []

# loop through stream and append audio chunks to frame array
for i in range(0, int((sample_rate/chunk_size) * record_secs)):
    data = stream.read(chunk_size)
    frames.append(data)

print("finished recording")

# stop the stream, close it, and terminate the pyaudio instantiation
stream.stop_stream()
stream.close()
audio.terminate()