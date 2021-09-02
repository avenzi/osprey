from lib.lib import Client
from lib.raspi.streamers import *

# Test streams
t1 = TestStreamer("Random 1", "Test Group 1")
t2 = TestStreamer("Random 2", "Test Group 1")

# Synth EEG Stream #1
synth1eeg = SynthEEGStreamer('Raw', 'Synth EEG 1')

video = VideoStreamer('Raw', 'Video 1')

audio = AudioStreamer('Raw', 'Audio 1')

sense = SenseStreamer('Raw', 'Sense Hat 1')

# Pass all workers to client
workers = [t1, t2, synth1eeg, video, sense, audio]

client = Client(
    workers=workers, name='Raspi #1', debug=1,
    server_ip='signalstream.org', port=443,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)
client.run()
