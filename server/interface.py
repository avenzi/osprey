from lib.lib import Interface, Page

from server.bokeh_layouts import eeg_layout, test_layout

# instantiate an interface object to be used by the Flask app
interface = Interface()

# todo: ability to add more pipelines for the other expected data streams

# todo: make the names given to these pages a "type" instead of an identifying name.
#  That way, multiple groups of the same type can be streamed in with different names
#  without having to create a new Page() object for each

# testing page with random data
test_0 = Page('Test Group 0',
              expected=['Random 1', 'Random 2'],
              layout=test_layout.create_stream_layout)

# live eeg stream page
eeg = Page('EEG',
           expected=['Raw', 'Filtered', 'Fourier', 'Headplot'],
           layout=eeg_layout.create_layout)

# synthetic eeg stream page
synth_eeg_1 = Page('Synth EEG 1',
                 expected=['Raw', 'Filtered', 'Fourier', 'Headplot'],
                 layout=eeg_layout.create_layout)



# video stream page
video = Page('Video 1', expected=['Raw'], html='video.html')

interface.add_pages(test_0, eeg, synth_eeg_1, video)







