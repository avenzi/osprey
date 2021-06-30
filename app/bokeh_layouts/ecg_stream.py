from bokeh.models import CustomJS, AjaxDataSource, DataRange1d
from bokeh.models import Panel, Tabs, ColorBar, LogColorMapper, LogTicker, PrintfTickFormatter
from bokeh.models import Slider, RangeSlider, Select, Spinner, Toggle, RadioButtonGroup
from bokeh.layouts import layout, Row, Column
from bokeh.transform import log_cmap
from bokeh.plotting import figure
from bokeh.palettes import viridis, magma

from json import loads

from app.bokeh_layouts.eeg_stream import js_request

BACKEND = 'canvas'  # 'webgl' appears to be broken - makes page unresponsive.

# default values of all widgets and figure attributes
default_config = {
    'fourier_window': 2,
    'spectrogram_range': (-3.0, 1.0),  # color scale range (log)
    'spectrogram_size': 30,

    'pass_toggle': True,
    'pass_type': 'bandpass',
    'pass_style': 'Butterworth',
    'pass_range': (1, 100),
    'pass_order': 3,
    'pass_ripple': (1, 50),

    'stop_toggle': True,
    'stop_type': 'bandstop',
    'stop_style': 'Butterworth',
    'stop_range': (59, 60.5),
    'stop_order': 5,
    'stop_ripple': (1, 50),
}


def create_layout(info):
    """
    Configures all Bokeh figures and plots
    <info> dict. keys are stream names assigned in this group.
        Values are dictionaries of the info given to that stream.
    """

    # get channel names
    sample_rate = float(info['Raw']['sample_rate'])
    pulse_channels = info['Raw']['pulse_channels'].split(',')  # it's a comma separated string
    ecg_channels = info['Raw']['ecg_channels'].split(',')  # it's a comma separated string

    channels = [pulse_channels[0]] + ecg_channels

    # get config
    config = info.get('widgets')
    if config:  # config present, it's a JSON string.
        config = loads(config)
        print('ECG SAVED CONFIG: {}'.format(config))
    else:  # no config present, use default
        config = default_config
        print('ECG DEFAULT CONFIG')

    # get stream IDs
    filtered_id = info['Filtered']['id']  # Filter Analyzer ID
    fourier_id = info['Fourier']['id']  # Fourier Analyzer ID

    # viridis color palette for channel colors
    colors = viridis(len(channels))

    ##########################
    # create row of widgets that send data to the analyzer streams
    # Fourier Window sliders
    fourier_window = Spinner(title="FFT Window (s)", low=1, high=10, step=1, width=90, value=config['fourier_window'])
    fourier_window.js_on_change("value", CustomJS(code=js_request(fourier_id, 'fourier_window')))

    # Toggle buttons
    pass_toggle = Toggle(label="Bandpass", button_type="success", width=100, margin=(24, 5, 0, 5), active=config['pass_toggle'])
    pass_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'pass_toggle', 'active')))

    stop_toggle = Toggle(label="Bandstop", button_type="success", width=100, margin=(24, 5, 0, 5), active=config['stop_toggle'])
    stop_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'stop_toggle', 'active')))

    # Range sliders. "value_throttled" only takes the slider value once sliding has stopped
    pass_range = RangeSlider(title="Range", start=0.1, end=100, step=0.1, value=config['pass_range'])
    pass_range.js_on_change("value_throttled", CustomJS(code=js_request(filtered_id, 'pass_range')))

    stop_range = RangeSlider(title="Range", start=40, end=70, step=0.5, value=config['stop_range'])
    stop_range.js_on_change("value_throttled", CustomJS(code=js_request(filtered_id, 'stop_range')))

    # filter style selectors
    pass_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['pass_style'])
    pass_style.js_on_change("value", CustomJS(code=js_request(filtered_id, 'pass_style')))

    stop_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['stop_style'])
    stop_style.js_on_change("value", CustomJS(code=js_request(filtered_id, 'stop_style')))

    # Order spinners
    pass_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=config['pass_order'])
    pass_order.js_on_change("value", CustomJS(code=js_request(filtered_id, 'pass_order')))

    stop_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=config['stop_order'])
    stop_order.js_on_change("value", CustomJS(code=js_request(filtered_id, 'stop_order')))

    # Used to construct the Bokeh layout of widgets
    widgets_row = [fourier_window, [[pass_toggle, pass_style, pass_order, pass_range], [stop_toggle, stop_style, stop_order, stop_range]]]

    ###################################
    # create AJAX data sources for the plots
    # the if_modified=True allows it to ignore responses sent with a 304 code.
    ecg_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(filtered_id),
        method='GET',
        polling_interval=500,
        mode='append',
        max_size=int(sample_rate*5),
        if_modified=True)

    fourier_source = AjaxDataSource(
        data_url='/stream/update?id={}&format=snapshot'.format(fourier_id),
        method='GET',
        polling_interval=500,
        mode='replace',  # all FFT lines are replaced each update
        if_modified=True)

    #############################################
    # create ECG figure with all ECG lines plotted on it
    # initial x_range must be set in order to disable auto-scaling
    # initial y_ranges should not be set to enable auto-scaling
    ecg = figure(
        title='ECG Channels',
        x_axis_label='Time (s)', y_axis_label='Voltage (uV)', x_range=[0, 0],
        plot_width=1200, plot_height=200,
        toolbar_location=None,
        output_backend=BACKEND
    )
    ecg.toolbar.active_drag = None  # disable drag

    # y-axis range will autoscale to currently selected channel
    ecg.y_range.only_visible = True

    for i in range(len(channels)):  # plot each line
        visible = True if i == 0 else False  # first channel visible
        ecg.line(x='time', y=channels[i], name=channels[i], color=colors[i], source=ecg_source, visible=visible)

    # Whenever the DataSource data changes, incrementally slide x_range over the length of the
    # new incoming data to give smooth appearance.
    # TODO: can it be made less choppy?
    ecg_source.js_on_change('data',
        CustomJS(args=dict(  # arguments to be passed into the JS function
            source=ecg_source,
            figure=ecg
        ),
            code="""
var duration = source.polling_interval
var current = figure.x_range.end

var end = source.data['time'][source.data['time'].length-1]
var start = source.data['time'][0]

var diff = end - current
if (diff > 0 && diff < end-start) {
    var slide = setInterval(function(){
        if (figure.x_range.end < end) {
            figure.x_range.start += diff/20
            figure.x_range.end += diff/20
        }

    }, duration/20);

    setTimeout(function(){
        clearInterval(slide)
        figure.x_range.start = start + diff
        figure.x_range.end = end
    }, duration)
} else {
    figure.x_range.start = start
    figure.x_range.end = end
}
"""
    ))

    # fourier figure with a line for each EEG channel
    fourier = figure(
        title="ECG Fourier",
        x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log",
        plot_width=1200, plot_height=400,
        tools='xpan,xwheel_zoom,reset', toolbar_location='above',
        output_backend=BACKEND
    )

    for i in range(len(channels)):
        fourier.line(x='frequencies', y=channels[i], color=colors[i], source=fourier_source)
    #fourier_panel = Panel(child=fourier, title='FFT')  # create a tab for this plot

    # Radio buttons to select channels on the EEG figure and Spectrogram figure
    channel_radios = RadioButtonGroup(labels=channels, active=0)
    channel_radios.js_on_click(CustomJS(
        args=dict(
            ecg_fig=ecg,
            labels=channels
        ),
        code="""
    ecg_fig.select_one(this.labels[this.active]).visible = true
    for (var label of labels) {
        if (label != this.labels[this.active]){
            ecg_fig.select_one(label).visible = false
        }
    }
    """))

    #################
    # Construct final layout
    #analysis_tabs = Tabs(tabs=[fourier_panel])
    full_layout = layout([channel_radios, ecg, widgets_row, fourier])
    return full_layout


