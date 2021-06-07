from lib.lib import Client
from lib.server.analyzers import *

# name, group_name, target_name, target_group (if not same group)

analyzers = [
    TestAnalyzer('Random Analyzer 1', 'TestGroup', 'Random 1'),
    TestAnalyzer('Random Analyzer 1', 'TestGroup 2', 'Random 1'),
    EEGFilterStream('Filtered EEG', 'EEG 1', 'Raw EEG'),
    EEGFourierStream('Fourier EEG', 'EEG 1', 'Filtered EEG')
]

config = 'config/server_streamer_config.json'

client = Client(analyzers, config, debug=2)
client.run()







