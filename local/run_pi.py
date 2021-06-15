from lib.raspi.pi_lib import RaspiClient
from lib.raspi.streamers import *

# initialize list of streamer instances
# Each must have a globally unique group name and a locally unique name within that group
# group_name, name
workers = [
    TestStreamer('TestGroup', 'Random 1'),
    TestStreamer('TestGroup', 'Random 2'),
    TestStreamer('TestGroup 2', 'Random 1'),
    SenseStreamer('SenseHat 1', 'Sense'),
    VideoStreamer('Video 1', 'Video'),
    SynthEEGStreamer('EEG 1', 'Raw')
]

client = RaspiClient(
    workers=workers, name='Raspi Client 1', debug=1,
    server_ip='3.131.117.61', port=5000,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)
client.run()




