from lib.raspi.pi_lib import RaspiClient
from lib.raspi.streamers import *

# initialize list of streamer instances
# Each must have a globally unique group name and a locally unique name within that group
# name, group_name
workers = [
    TestStreamer('Random 1', 'TestGroup'),
    TestStreamer('Random 2', 'TestGroup'),
    TestStreamer('Random 1', 'TestGroup 2'),
    SenseStreamer('Sense Hat', 'SenseHat 1'),
    VideoStreamer('Video', 'Video 1'),
    SynthEEGStreamer('Raw EEG', 'EEG 1')
]

client = RaspiClient(
    workers=workers, name='Raspi Client 1', debug=2,
    server_ip='3.131.117.61', port=5000,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)
client.run()




