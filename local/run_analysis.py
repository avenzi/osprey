from lib.lib import Client
from lib.server.analyzers import *
from lib.raspi.streamers import *

# name, group_name, target_name, target_group (if not same group)

workers = [
    TestAnalyzer('Random Analyzer 1', 'TestGroup', 'Random 1'),
    TestAnalyzer('Random Analyzer 1', 'TestGroup 2', 'Random 1'),
    EEGFilterStream('Filtered EEG', 'EEG 1', 'Raw EEG'),
    EEGFourierStream('Fourier EEG', 'EEG 1', 'Filtered EEG'),
    EEGFilterStream('Filtered EEG', 'EEG 2', 'Raw EEG'),
    EEGFourierStream('Fourier EEG', 'EEG 2', 'Filtered EEG')
]

client = Client(
    workers=workers, name='AWS Local Client', debug=2,
    server_ip='3.131.117.61', port=5000,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)
client.run()







