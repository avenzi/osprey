from app.bokeh_layouts import test_stream, eeg_stream, sense_stream

# html stream pages associated with each group
pages = {
    'TestGroup': 'bokeh_plot.html',
    'TestGroup 2': 'bokeh_plot.html',
    'SenseHat 1': 'bokeh_plot.html',
    'EEG 1': 'bokeh_plot.html',
    'Video 1': 'video.html'
}

# Bokeh layout functions associated with each group
bokeh_layouts = {
    'TestGroup': test_stream.create_layout,
    'TestGroup 2': test_stream.create_layout,
    'SenseHat 1': sense_stream.create_layout,
    'EEG 1': eeg_stream.create_layout,
}