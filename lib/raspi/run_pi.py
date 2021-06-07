from lib.raspi.pi_lib import RaspiClient
from lib.raspi.streamers import *

# initialize list of streamer instances
# Each must have a globally unique group name and a locally unique name within that group
# name, group_name
streamers = [
    TestStreamer('Random 1', 'TestGroup'),
    TestStreamer('Random 2', 'TestGroup'),
    TestStreamer('Random 1', 'TestGroup 2'),
    TestStreamer('Random 2', 'TestGroup 2'),
    SenseStreamer('Sense Hat', 'SenseHat 1'),
    SynthEEGStreamer('Raw EEG', 'EEG 1')
]

config = 'config/raspi_config.json'

client = RaspiClient(streamers, config, debug=2)
client.run()




