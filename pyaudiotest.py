import sounddevice as sd

sd.default.samplerate = 44100
sd.default.channels = 1
myrecording = sd.rec(int(5 * sd.default.samplerate), samplerate=sd.default.samplerate, channels=1)
sd.wait()
print(len(myrecording))
