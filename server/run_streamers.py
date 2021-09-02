from lib.lib import Client
from server.analyzers import *
from lib.raspi.streamers import *

# Test analyzer, targeting 2 random streamers from 2 different groups
ta = TestAnalyzer('Random Analyzer', 'Test Analyzer')
ta.target('Random 1', 'Test Group 1')
ta.target('Random 2', 'Test Group 1')
ta.target('Random 1', 'Test Group 2')
ta.target('Random 2', 'Test Group 2')

t0func = FunctionAnalyzer('Transformed', 'Test Group 0')
t0func.target('Random 2')
t0func.target('Random 1')

t1func = FunctionAnalyzer('Transformed', 'Test Group 1')
t1func.target('Random 2')
t1func.target('Random 1')

t2func = FunctionAnalyzer('Transformed', 'Test Group 2')
t2func.target('Random 2')
t2func.target('Random 1')


# Synthetic EEG stream #1
synth1filt = EEGFilter('Filtered', 'Synth EEG 1')
synth1filt.target('Raw')

synth1four = EEGFourier('Fourier', 'Synth EEG 1')
synth1four.target('Filtered')
synth1four.target('Raw')

synth1func = FunctionAnalyzer('Transformed', 'Synth EEG 1')
synth1func.target('Filtered')

# Synthetic EEG stream #2
synth2filt = EEGFilter('Filtered', 'Synth EEG 2')
synth2filt.target('Raw')

synth2four = EEGFourier('Fourier', 'Synth EEG 2')
synth2four.target('Filtered')
synth2four.target('Raw')

synth2func = FunctionAnalyzer('Transformed', 'Synth EEG 2')
synth2func.target('Filtered')

# Live EEG Stream
eegfilt = EEGFilter('Filtered', 'EEG')
eegfilt.target('Raw')

eegfour = EEGFourier('Fourier', 'EEG')
eegfour.target('Filtered')
eegfour.target('Raw')
eegfunc = FunctionAnalyzer('Transformed','EEG')
eegfunc.target('Filtered')

# Live ECG Stream
ecgfilt = ECGFilter('Filtered', 'ECG')
ecgfilt.target('Raw')

ecgfour = ECGFourier('Fourier', 'ECG')
ecgfour.target('Filtered')
ecgfour.target('Raw')
ecgfunc = FunctionAnalyzer("Transformed", "ECG")
ecgfunc.target('Filtered')

# Test stream for no PI
t1 = TestStreamer("Random 1", "Test Group 0")
t2 = TestStreamer("Random 2", "Test Group 0")
synth1 = SynthEEGStreamer('Raw', 'Synth EEG 1')

# Pass all workers to client
worker_no_pi_test = [t1, t2, t0func, synth1, synth1filt, synth1four, synth1func]
workers_test = [synth1filt, synth1four, t1func]
workers = [eegfilt, eegfour, eegfunc, ecgfilt, ecgfour, ecgfunc]

client = Client(
    workers=workers_test, name='AWS Local Client', debug=1,
    server_ip='signalstream.org', port=443,
    db_port=5001, db_pass='thisisthepasswordtotheredisserver'
)

client.run()