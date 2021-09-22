from lib.server.server_lib import Interface, Page

from server.bokeh_layouts import eeg_layout, ecg_layout, test_layout, sense_layout, audio_layout

# instantiate an interface object to be used by the Flask app
interface = Interface()

# Sense Hat pages
for name in ['Sense Hat 1', 'Sense Hat 2']:
    page = Page(name, ['Raw'], layout=sense_layout.create_layout)
    interface.add_pages(page)

# testing pages with random data
for name in ['Test Group 0', 'Test Group 1', 'Test Group 2']:
    expected = ['Random 1', 'Random 2']
    page = Page(name, expected, layout=test_layout.create_stream_layout)
    interface.add_pages(page)

# EEG stream pages
for name in ['EEG', 'Synth EEG 1', 'Synth EEG 2']:
    expected = ['Raw', 'Filtered', 'Fourier', 'Headplot']
    page = Page(name, expected, layout=eeg_layout.create_layout)
    interface.add_pages(page)

# ECG stream page
expected = ['Raw', 'Filtered', 'Fourier']
page = Page('ECG', expected, layout=ecg_layout.create_layout)
interface.add_pages(page)

# video stream page
for name in ['Video 1', 'Video 2']:
    page = Page(name, ['Raw'], html='video.html')
    interface.add_pages(page)


for name in ['Audio 1', 'Audio 2']:
    page = Page(name, ['Audio'], layout=audio_layout.create_layout)
    interface.add_pages(page)






