from bokeh.models import CustomJS, AjaxDataSource, DataRange1d
from bokeh.models import Panel, Tabs, ColorBar, LogColorMapper, LogTicker, PrintfTickFormatter
from bokeh.models import Slider, RangeSlider, Select, Spinner, Toggle, RadioButtonGroup
from bokeh.layouts import layout, Row, Column
from bokeh.transform import log_cmap
from bokeh.plotting import figure
from bokeh.palettes import viridis, magma

import json
from scipy import signal

BACKEND = 'canvas'  # 'webgl' appears to be broken - makes page unresponsive.

# default values of all widgets and figure attributes
config = {
    'fourier_window': 5,
    'spectrogram_range': (-3.0, 1.0),  # color scale range (log)
    'spectrogram_size': 30,

    'pass_toggle': False,
    'pass_type': 'bandpass',
    'pass_style': 'Butterworth',
    'pass_range': (1, 60),
    'pass_order': 3,
    'pass_ripple': (1, 50),

    'stop_toggle': False,
    'stop_type': 'bandstop',
    'stop_style': 'Butterworth',
    'stop_range': (59, 60.5),
    'stop_order': 2,
    'stop_ripple': (1, 50),

    'bands': {'Delta': (1, 4), 'Theta': (4, 8), 'Alpha': (8, 12), 'Beta': (12, 30), 'Gamma': (30, 100)}
}


def js_request(key, attribute='value'):
    """
    Generates callback JS code to send an HTTPRequest
    'this.value' refers to the new value of the Bokeh object.
        - In some cases (like buttons) Bokeh uses 'this.active'
    <key> is the key in the JSON string being sent to associate with this value
    """
    widget_path = 'widgets'  # request path

    code = """
        var req = new XMLHttpRequest();
        url = window.location.pathname;
        queries = window.location.search;  // get ID of current stream
        req.open("POST", url+'/{path}'+queries, true);
        req.setRequestHeader('Content-Type', 'application/json');
        var json = JSON.stringify({{{key}: this.{attribute}}});
        req.send(json);
        console.log('{key}: ' + this.{attribute});
    """
    return code.format(path=widget_path, key=key, attribute=attribute)


# Fourier Window sliders
fourier_window = Spinner(title="FFT Window (s)", low=1, high=10, step=1, width=90, value=config['fourier_window'])
fourier_window.js_on_change("value", CustomJS(code=js_request('fourier_window')))

# Toggle buttons
pass_toggle = Toggle(label="Bandpass", button_type="success", width=100, margin=(24, 5, 0, 5), active=config['pass_toggle'])
pass_toggle.js_on_click(CustomJS(code=js_request('pass_toggle', 'active')))

stop_toggle = Toggle(label="Bandstop", button_type="success", width=100, margin=(24, 5, 0, 5), active=config['stop_toggle'])
stop_toggle.js_on_click(CustomJS(code=js_request('stop_toggle', 'active')))

# Range sliders
pass_range = RangeSlider(title="Range", start=0.1, end=100, step=0.1, value=config['pass_range'])
pass_range.js_on_change("value_throttled", CustomJS(code=js_request('pass_range')))

stop_range = RangeSlider(title="Range", start=40, end=70, step=0.5, value=config['stop_range'])
stop_range.js_on_change("value_throttled", CustomJS(code=js_request('stop_range')))

# filter style selectors
pass_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['pass_style'])
pass_style.js_on_change("value", CustomJS(code=js_request('pass_style')))

stop_style = Select(title="Filters:", width=110, options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['stop_style'])
stop_style.js_on_change("value", CustomJS(code=js_request('stop_style')))

# Order spinners
pass_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=config['pass_order'])
pass_order.js_on_change("value", CustomJS(code=js_request('pass_order')))

stop_order = Spinner(title="Order", low=1, high=10, step=1, width=60, value=config['stop_order'])
stop_order.js_on_change("value", CustomJS(code=js_request('stop_order')))

# Used to construct the Bokeh layout of widgets
widgets_row = [fourier_window, [[pass_toggle, pass_style, pass_order, pass_range], [stop_toggle, stop_style, stop_order, stop_range]]]


# Bokeh Figures
def create_layout(info):
    """
    Configures all Bokeh figures and plots
    <info> must contain a 'channels' key
    """
    # TODO: Split this up into more easily digestible chunks?
    # TODO: Remove Spectrogram for good. Too much data is required to make it worth while,
    #  and it's not necessary because of the headplots. Will need to remove the AjaxDataSource,
    #  spectrogram image and figure creation, the JS callback from the radio buttons targetting the
    #  spec images, the spectrogram Tab creation, and the code adding/sending data to the browser in
    #  the EEGHandler class.
    stream_id = info['id']
    stream_channels = info['channels']
    print("Channels in create_layout: ", stream_channels)

    colors = viridis(len(stream_channels))  # viridis color palette for channel colors

    # create AJAX data sources for the plots
    # the if_modified=True allows it to ignore responses sent with a 304 code.
    eeg_source = AjaxDataSource(
        data_url='/update_eeg?id={}'.format(stream_id),
        method='GET',
        polling_interval=1000,
        mode='append',
        max_size=2000,
        if_modified=True)

    fourier_source = AjaxDataSource(
        data_url='/update_fourier?id={}'.format(stream_id),
        method='GET',
        polling_interval=1000,
        mode='replace',  # all FFT lines are replaced each update
        if_modified=True)

    '''  # Spectrogram (to remove)
    spectrogram_source = AjaxDataSource(
        data_url='/update_spectrogram?id={}'.format(worker_id),
        method='GET',
        polling_interval=5000,
        max_size=config['spectrogram_size'],
        mode='append',  # new Spectrogram slices are appended each update
        if_modified=True)
    '''

    headplot_source = AjaxDataSource(
        data_url='/update_headplot?id={}'.format(stream_id),
        method='GET',
        polling_interval=1000,
        mode='replace',
        if_modified=True)

    ##############
    # create EEG figure with all EEG lines plotted on it
    # initial x_range must be set in order to disable auto-scaling
    # initial y_ranges should not be set to enable auto-scaling
    eeg = figure(
        title='EEG Channels',
        x_axis_label='Time (s)', y_axis_label='Voltage (uV)', x_range=[0, 0],
        plot_width=1200, plot_height=200,
        toolbar_location=None, active_scroll=None, active_drag=None,
        output_backend=BACKEND
    )

    # y-axis range will autoscale to currently selected channel
    eeg.y_range.only_visible = True

    for i in range(len(channels)):  # plot each line
        visible = True if i == 0 else False  # first channel visible
        eeg.line(x='time', y=channels[i], name=channels[i], color=colors[i], source=eeg_source, visible=visible)

    # Whenever the DataSource data changes, incrementally slide x_range
    # to give the appearance of continuity.
    # TODO: make it less choppy?
    eeg_source.js_on_change('data',
                            CustomJS(args=dict(  # arguments to be passed into the JS function
                                source=eeg_source,
                                figure=eeg
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
        title="EEG Fourier",
        x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log",
        plot_width=1200, plot_height=400,
        toolbar_location=None, active_drag=None, active_scroll=None,
        output_backend=BACKEND
    )
    for i in range(len(channels)):
        fourier.line(x='frequencies', y=channels[i], color=colors[i], source=fourier_source)
    fourier_panel = Panel(child=fourier, title='FFT')  # create a tab for this plot

    ################
    # Color mapper for the headplot ColorBar
    mapper_low = 10 ** (config['spectrogram_range'][0])  # low threshold
    mapper_high = 10 ** (config['spectrogram_range'][1])  # high threshold
    mapper_palette = magma(20)
    mapper = LogColorMapper(palette=mapper_palette, low=mapper_low, high=mapper_high)
    tick_formatter = PrintfTickFormatter(format="%1e")
    color_bar = ColorBar(
        color_mapper=mapper,
        ticker=LogTicker(),
        formatter=tick_formatter,
        label_standoff=15,
        border_line_color=None,
        location=(0, 0)
    )

    '''  # Spectrogram stuff. (to remove)
    # Spectrogram data source has 'slice' and 'spec_time' as data lists.
    # 'slice' is a list of images (2D lists), that have only 1 row, but they still must be
    #       passed as a 2D list. The image is a heatmap of the FFT for that slice.
    # 'spec_time' is a list of numbers representing the 'time index' of a particular slice.
    #       This value is used to stack the images on top of each other, and is simply
    #       incremented whenever a slice is sent.

    # First plot a full spectrogram of nothing so new data is added proportionally.
    spectrogram_source.data = {'spec_time': [i for i in range(config['spectrogram_size'])]}
    for name in channels:
        spectrogram_source.data[name] = [[[0]] for i in range(config['spectrogram_size'])]

    # create a spectrogram figure
    spec = figure(
        title="EEG Spectrogram",
        x_axis_label='Frequency (Hz)', y_axis_label='Time (index)',
        plot_width=1200, plot_height=500,
        toolbar_location=None, active_drag=None, active_scroll=None,
    )
    spec.background_fill_color = "black"
    spec.add_layout(color_bar, 'left')
    spec.grid.visible = False

    # image glyphs
    for i in range(len(channels)):  # image for each channel
        visible = True if i == 0 else False  # first channel visible
        spec.image(
            image=channels[i], x=0, y='spec_time', dw=60, dh=1,
            color_mapper=mapper, source=spectrogram_source,
            name=channels[i], visible=visible
        )

    spectrogram_slider = RangeSlider(
        title='',
        start=-10, end=3, step=1,  # log scale
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=config['spectrogram_range'])

   spectrogram_slider.js_on_change(
        "value",
        CustomJS(args=dict(  # arguments to be passed into the JS function
            fig=spec,
            names=channels,
            source=spectrogram_source,
            color_bar=color_bar
        ),
            code="""
var low = Math.pow(10, this.value[0]);
var high = Math.pow(10, this.value[1]);

if (low < high) {
    color_bar.color_mapper.low = low;
    color_bar.color_mapper.high = high;
    for (name of names) {
        var image = fig.select_one(name)
        image.glyph.color_mapper.low = low;
        image.glyph.color_mapper.high = high;
    }
    source.change.emit();
}
"""
        ))
    '''

    # Radio buttons to select channels on the EEG figure and Spectrogram figure
    channel_radios = RadioButtonGroup(labels=channels, active=0)
    channel_radios.js_on_click(CustomJS(
        args=dict(
            eeg_fig=eeg,
            labels=channels
        ),
        code="""
    eeg_fig.select_one(this.labels[this.active]).visible = true
    // spec_fig.select_one(this.labels[this.active]).visible = true
    for (var label of labels) {
        if (label != this.labels[this.active]){
            eeg_fig.select_one(label).visible = false
            // spec_fig.select_one(label).visible = false
        }
    }
    """))

    ################
    # Head Plots

    # get 2D positions of all possible headset electrodes
    with open(PAGES_PATH + '/electrodes.json', 'r') as f:
        all_names = json.loads(f.read())

    x, y = [], []
    for name in channels:  # get coordinates of electrodes by name
        x.append(all_names[name][0])
        y.append(all_names[name][1])

    # Separate head figure for each band
    head_figures = []  # list of headplot figures
    circles = []  # list of circle glyphs used to update the color mapping
    for band in config['bands']:
        fig = figure(
            title='{}-band Head Plot'.format(band),
            plot_width=300, plot_height=300,
            toolbar_location=None, active_drag=None, active_scroll=None,
            output_backend=BACKEND
        )
        # Even though x and y don't change, they have to be gotten from the data source.
        # Each figure gets its own color mapper and takes data from the
        #   column with it's band name, which contains the color data.
        mapper = log_cmap(field_name=band, palette=mapper_palette, low=mapper_low, high=mapper_high)
        circle = fig.circle(x='x', y='y', source=headplot_source, color=mapper, size=20)
        fig.xaxis.ticker, fig.xaxis.ticker = [], []  # disable axes
        head_figures.append(fig)
        circles.append(circle)

    delta, theta, alpha, beta, gamma = head_figures  # figures
    delta_c, theta_c, alpha_c, beta_c, gamma_c = circles  # glyphs

    # put colorbar on left-most plot and increase width to accomodate
    delta.add_layout(color_bar, 'left')
    delta.plot_width = 390  # this seems to be the right amount (visually)

    # Headplot color scale adjusting slider.
    # This widget needs to be here (as opposed to at the top with all the other widgets) because
    # it needs to get references to all the arguments for the CustomJS.
    # None of the other widgets are in this function because they don't require references.
    headplot_slider = RangeSlider(
        title='',
        start=-10, end=3, step=1,  # log scale
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=config['spectrogram_range'])

    headplot_slider.js_on_change(
        "value",
        CustomJS(args=dict(  # arguments to be passed into the JS function
            color_bar=color_bar, palette=mapper_palette, source=headplot_source,
            delta=delta_c, theta=theta_c, alpha=alpha_c, beta=beta_c, gamma=gamma_c
        ),
            code="""
var low = Math.pow(10, this.value[0]);
var high = Math.pow(10, this.value[1]);
if (low < high) {
    var color_mapper = new Bokeh.LogColorMapper({palette:palette, low:low, high:high});

    color_bar.color_mapper = color_mapper

    delta.glyph.fill_color = {field: "Delta", transform: color_mapper};
    delta.glyph.line_color = {field: "Delta", transform: color_mapper};
    theta.glyph.fill_color = {field: "Theta", transform: color_mapper};
    theta.glyph.line_color = {field: "Theta", transform: color_mapper};
    alpha.glyph.fill_color = {field: "Alpha", transform: color_mapper};
    alpha.glyph.line_color = {field: "Alpha", transform: color_mapper};
    beta.glyph.fill_color = {field: "Beta", transform: color_mapper};
    beta.glyph.line_color = {field: "Beta", transform: color_mapper};
    gamma.glyph.fill_color = {field: "Gamma", transform: color_mapper};
    gamma.glyph.line_color = {field: "Gamma", transform: color_mapper};
    source.change.emit();
}
"""
        )
    )

    '''  # spectrogram Tab (to remove)
    # Panel for spectrogram has the range slider in it
    spec_panel = Panel(child=Row(spectrogram_slider, spec), title='Spectrogram')
    '''

    # Panel for head plots
    head_panel = Panel(child=Row(headplot_slider, delta, theta, alpha, beta, gamma), title='Head Plots')  # create a tab for head plots

    #################
    # Construct final layout
    analysis_tabs = Tabs(tabs=[fourier_panel, head_panel])
    full_layout = layout([channel_radios, eeg, widgets_row, analysis_tabs])
    return full_layout


def create_filter_sos(name, sample_rate, config):
    """
    Returns the Second Order Sections of the given filter design.
    [name] prefix used to get config attributes
    [sample rate] int: Number of samples per second
    [config] dict: Configuration dictionary seen at the top of this file. Must contain:
        [name_type] string: bandpass, bandstop, lowpass, highpass
        [name_style] string: Bessel, Butterworth, Chebyshev 1, Chebyshev 2, Elliptic
        [name_crit] tuple: (low, high) critical values for the filter cutoffs
        [name_order] int: Order of filter polynomial
        [name_ripple] tuple: (max gain, max attenuation) for chebyshev and elliptic filters
    """
    type = config[name + '_type']
    style = config[name + '_style']
    range = config[name + '_range']
    order = config[name + '_order']
    ripple = config[name + '_ripple']

    if style == 'Bessel':
        sos = signal.bessel(order, range, fs=sample_rate, btype=type, output='sos')
    elif style == 'Butterworth':
        sos = signal.butter(order, range, fs=sample_rate, btype=type, output='sos')
    elif style == 'Chebyshev 1':
        sos = signal.cheby1(order, ripple[0], range, fs=sample_rate, btype=type, output='sos')
    elif style == 'Chebyshev 2':
        sos = signal.cheby2(order, ripple[1], range, fs=sample_rate, btype=type, output='sos')
    elif style == 'Elliptic':
        sos = signal.ellip(order, ripple[0], ripple[1], range, fs=sample_rate, btype=type, output='sos')
    else:
        return None
    return sos

