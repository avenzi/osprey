from lib.lib import Client
from lib.server.analyzers import *
from lib.raspi.streamers import *

# group_name, name, target_name, optional target_group (if not same group)

workers = [
    TestAnalyzer('TestGroup', 'Random Analyzer 1', 'Random 1'),
    TestAnalyzer('TestGroup 2', 'Random Analyzer 1', 'Random 1'),
    EEGFilterStream('Synth EEG 1', 'Filtered', 'Raw'),
    EEGFourierStream('Synth EEG 1', 'Fourier', 'Filtered'),
    EEGFilterStream('Synth EEG 2', 'Filtered', 'Raw'),
    EEGFourierStream('Synth EEG 2', 'Fourier', 'Filtered'),
    EEGFilterStream('EEG 3', 'Filtered', 'Raw'),
    EEGFourierStream('EEG 3', 'Fourier', 'Filtered')
]

client = Client(
    workers=workers, name='AWS Local Client', debug=1,
    server_ip='3.131.117.61', port=5000,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)
client.run()







