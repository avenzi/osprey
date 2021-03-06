from bokeh.models import CustomJS, AjaxDataSource
from bokeh.models import RangeSlider, Select, Spinner, Toggle, RadioButtonGroup
from bokeh.layouts import layout
from bokeh.plotting import figure

from json import loads

from server.bokeh_layouts.utils import js_request, time_format, plot_sliding_js, plot_priority_js

BACKEND = 'canvas'  # 'webgl' appears to be broken - makes page unresponsive.

# default values of all widgets and figure attributes
default_filter_widgets = {
    'pass_toggle': False,
    'pass_type': 'bandpass',
    'pass_style': 'Butterworth',
    'pass_range': (100, 4000),
    'pass_order': 3,
    'pass_ripple': (1, 50),

    'stop_toggle': False,
    'stop_type': 'bandstop',
    'stop_style': 'Butterworth',
    'stop_range': (58, 61),
    'stop_order': 5,
    'stop_ripple': (1, 50),
}

default_fourier_widgets = {
    'fourier_window': 0.2,
    'spectrogram_range': (-3.0, 1.0),  # color scale range (log)
    'spectrogram_size': 30,
}

def create_layout(info):
    """
    Configures all Bokeh figures and plots
    <info> dict. keys are stream names assigned in this group.
        Values are dictionaries of the info given to that stream.
    """

    # get channel names
    sample_rate = 500  # downsampled to 500Hz

    decoded_id = info['Decoded Audio']['id']
    filtered_id = info['Filtered']['id']
    fourier_id = info['Fourier']['id']


    # get filter widget values
    filter_widgets = info['Filtered'].get('widgets')
    if filter_widgets:  # config present, it's a JSON string.
        filter_widgets = loads(filter_widgets)
    else:  # no config present, use default
        filter_widgets = default_filter_widgets

    # get fourier widget values
    fourier_widgets = info['Fourier'].get('widgets')
    if fourier_widgets:  # config present, it's a JSON string.
        fourier_widgets = loads(fourier_widgets)
    else:  # no config present, use default
        fourier_widgets = default_fourier_widgets

    ##########################
    # create row of widgets that send data to the analyzer streams
    # Fourier Window sliders
    fourier_window = Spinner(title="FFT Window (s)", low=0.1, high=5, step=0.1, width=90, value=fourier_widgets['fourier_window'])
    fourier_window.js_on_change("value", CustomJS(code=js_request(fourier_id, 'fourier_window')))

    # Toggle buttons
    pass_toggle = Toggle(label="Bandpass", button_type="success", width=100, margin=(24, 5, 0, 5), active=filter_widgets['pass_toggle'])
    pass_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'pass_toggle', 'active')))

    stop_toggle = Toggle(label="Bandstop", button_type="success", width=100, margin=(24, 5, 0, 5), active=filter_widgets['stop_toggle'])
    stop_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'stop_toggle', 'active')))

    # Range sliders. "value_throttled" only takes the slider value once sliding has stopped
    pass_range = RangeSlider(title="Range", start=0, end=8000, step=100, value=filter_widgets['pass_range'])
    pass_range.js_on_change("value_throttled", CustomJS(code=js_request(filtered_id, 'pass_range')))

    stop_range = RangeSlider(title="Range", start=0, end=8000, step=100, value=filter_widgets['stop_range'])
    stop_range.js_on_change("value_throttled", CustomJS(code=js_request(filtered_id, 'stop_range')))

    # filter style selectors
    pass_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=filter_widgets['pass_style'])
    pass_style.js_on_change("value", CustomJS(code=js_request(filtered_id, 'pass_style')))

    stop_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=filter_widgets['stop_style'])
    stop_style.js_on_change("value", CustomJS(code=js_request(filtered_id, 'stop_style')))

    # Order spinners
    pass_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=filter_widgets['pass_order'])
    pass_order.js_on_change("value", CustomJS(code=js_request(filtered_id, 'pass_order')))

    stop_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=filter_widgets['stop_order'])
    stop_order.js_on_change("value", CustomJS(code=js_request(filtered_id, 'stop_order')))

    # Used to construct the Bokeh layout of widgets
    widgets_row = [fourier_window, [[pass_toggle, pass_style, pass_order, pass_range], [stop_toggle, stop_style, stop_order, stop_range]]]

    ###################################
    # create AJAX data sources for the plots
    # the if_modified=True allows it to ignore responses sent with a 304 code.
    audio_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(decoded_id),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=int(sample_rate*5),  # Keep last 5 seconds
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    filtered_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(filtered_id),
        method='GET',
        polling_interval=1000,
        mode='append',
        max_size=int(sample_rate*5),
        if_modified=True)

    fourier_source = AjaxDataSource(
        data_url='/stream/update?id={}&format=snapshot'.format(fourier_id),
        method='GET',
        polling_interval=1000,
        mode='replace',  # all FFT lines are replaced each update
        if_modified=True)

    #############################################
    # create raw audion figure
    # initial x_range must be set in order to disable auto-scaling
    # initial y_ranges should not be set to enable auto-scaling
    audio = figure(
        title='Audio Waveform',
        x_axis_label='Time (s)', y_axis_label='Magnitude',
        plot_width=1200, plot_height=200,
        toolbar_location=None,
        output_backend=BACKEND
    )
    audio.toolbar.active_drag = None  # disable drag
    audio.xaxis.formatter = time_format()

    # y-axis range will autoscale to currently selected channel
    audio.y_range.only_visible = True
    audio.line(x='time', y='data', color='blue', source=audio_source)
    audio.line(x='time', y='data', color='blue', source=filtered_source)

    plot_sliding_js(audio, audio_source)  # incoming data smoothing
    plot_priority_js(audio, back_source=audio_source, front_source=filtered_source)  # give transformed data priority

    # fourier figure with a line for each EEG channel
    fourier = figure(
        title="Audio Fourier",
        x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log",
        plot_width=1200, plot_height=300,
        tools='xpan,xwheel_zoom,reset', toolbar_location='above',
        output_backend=BACKEND
    )
    fourier.line(x='frequencies', y='data', source=fourier_source)

    #################
    # Construct final layout
    full_layout = layout([audio, widgets_row, fourier])
    return full_layout


