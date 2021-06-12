from lib.lib import Client
from lib.server.analyzers import *
from lib.raspi.streamers import *

# name, group_name, target_name, target_group (if not same group)

workers = [
    TestAnalyzer('Random Analyzer 1', 'TestGroup', 'Random 1'),
    TestAnalyzer('Random Analyzer 1', 'TestGroup 2', 'Random 1'),
    TestStreamer('Random 2', 'TestGroup 2'),  # regular streamer
    EEGFilterStream('Filtered EEG', 'EEG 1', 'Raw EEG'),
    EEGFourierStream('Fourier EEG', 'EEG 1', 'Filtered EEG')
]

config = 'config/server_streamer_config.json'

client = Client(workers, config, debug=2)
client.run()







