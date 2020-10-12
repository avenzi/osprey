from bokeh.models import CustomJS, AjaxDataSource
from bokeh.models import Panel, Tabs, ColorBar, LogColorMapper, LogTicker
from bokeh.models import Slider, RangeSlider, Select, Spinner, Toggle
from bokeh.layouts import layout, Row, Column
from bokeh.transform import linear_cmap
from bokeh.plotting import figure
from bokeh.palettes import viridis, magma

import json
from scipy import signal


# default values of all widgets and figure attributes
config = {'fourier_window': 5,
          'spectrogram_range': (-9.0, -2.0),  # color scale range (log)
          'spectrogram_size': 30,

          'pass_toggle': True,
          'pass_type': 'bandpass',
          'pass_style': 'Butterworth',
          'pass_range': (1, 60),
          'pass_order': 3,
          'pass_ripple': (1, 50),

          'stop_toggle': True,
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
        url = window.location.pathname
        queries = window.location.search  // get ID of current stream
        req.open("POST", url+'/{path}'+queries, true);
        req.setRequestHeader('Content-Type', 'application/json');
        var json = JSON.stringify({{{key}: this.{attribute}}});
        req.send(json);
        console.log('{key}: ' + this.{attribute});
    """
    return code.format(path=widget_path, key=key, attribute=attribute)


# Fourier Window sliders
fourier_window = Slider(title="FFT Window (seconds)", start=1, end=10, step=1, value=config['fourier_window'])
fourier_window.js_on_change("value_throttled", CustomJS(code=js_request('fourier_window')))

# Toggle buttons
pass_toggle = Toggle(label="Bandpass Filter", button_type="success", width=100, active=config['pass_toggle'])
pass_toggle.js_on_click(CustomJS(code=js_request('pass_toggle', 'active')))

stop_toggle = Toggle(label="Bandstop Filter", button_type="success", width=100, active=config['stop_toggle'])
stop_toggle.js_on_click(CustomJS(code=js_request('stop_toggle', 'active')))

# Range sliders
pass_range = RangeSlider(title="Range", start=0.1, end=100, step=0.1, value=config['pass_range'])
pass_range.js_on_change("value_throttled", CustomJS(code=js_request('pass_range')))

stop_range = RangeSlider(title="Range", start=40, end=70, step=0.5, value=config['stop_range'])
stop_range.js_on_change("value_throttled", CustomJS(code=js_request('stop_range')))

# filter style selectors
pass_style = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['pass_style'])
pass_style.js_on_change("value", CustomJS(code=js_request('pass_style')))

stop_style = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['stop_style'])
stop_style.js_on_change("value", CustomJS(code=js_request('stop_style')))

# Order spinners
pass_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=config['pass_order'])
pass_order.js_on_change("value", CustomJS(code=js_request('pass_order')))

stop_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=config['stop_order'])
stop_order.js_on_change("value", CustomJS(code=js_request('stop_order')))

# Used to construct the Bokeh layout of widgets
widgets_row = [[[pass_toggle, pass_style, pass_order], pass_range,
               [stop_toggle, stop_style, stop_order], stop_range, fourier_window]]


# Bokeh Figures
def configure_layout(worker_id, channels):
    """
    Configures all Bokeh figures and plots
    :param worker_id: Id of the WorkerNode (just self.id)
    :param channels: List of EEG channels being plotted.
    :return:
    # TODO: Split this up into more easily digestible chunks
    """
    colors = viridis(len(channels))  # viridis color palette for channel colors
    #tools = ['save']  # specify list of tool names for the toolbars. Will need to enable toolbars.

    # create AJAX data sources for the plots
    eeg_source = AjaxDataSource(
        data_url='/update_eeg?id={}'.format(worker_id),
        method='GET',
        polling_interval=1000,
        mode='append',
        max_size=1000,
        if_modified=True)

    fourier_source = AjaxDataSource(
        data_url='/update_fourier?id={}'.format(worker_id),
        method='GET',
        polling_interval=1000,
        mode='replace',  # all FFT lines are replaced each update
        if_modified=True)

    spectrogram_source = AjaxDataSource(
        data_url='/update_spectrogram?id={}'.format(worker_id),
        method='GET',
        polling_interval=1000,
        max_size=config['spectrogram_size'],
        mode='append',  # new Spectrogram slices are appended each update
        if_modified=True)

    headplot_source = AjaxDataSource(
        data_url='/update_headplot?id={}'.format(worker_id),
        method='GET',
        polling_interval=1000,
        mode='replace',
        if_modified=True)


    ##############
    # create EEG figures, each with it's own line
    eeg_list = []
    for i in range(len(channels)):
        eeg = figure(
            title=channels[i],
            x_axis_label='time', y_axis_label='Voltage',
            plot_width=600, plot_height=150,
            toolbar_location=None
        )
        eeg.line(x='time', y=channels[i], color=colors[i], source=eeg_source)
        eeg_list.append(eeg)

    # fourier figure with a line for each EEG channel
    fourier = figure(
        title="EEG Fourier",
        x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)',
        plot_width=700, plot_height=500,
        y_axis_type="log", toolbar_location=None
    )
    for i in range(len(channels)):
        fourier.line(x='frequencies', y=channels[i], color=colors[i], source=fourier_source)
    fourier_tab = Panel(child=fourier, title='FFT')  # create a tab for this plot


    ################
    # Color mapper for spectrogram
    low = 10**(config['spectrogram_range'][0])  # low threshold
    high = 10**(config['spectrogram_range'][1])  # high threshold
    palette = magma(20)
    mapper = LogColorMapper(palette=palette, low=low, high=high)
    color_bar = ColorBar(
        color_mapper=mapper,
        ticker=LogTicker(),
        label_standoff=5,
        border_line_color=None,
        location=(0, 0)
    )

    # Spectrogram data source has 'slice' and 'spec_time' as data lists.
    # 'slice' is a list of images (2D lists), that have only 1 row, but they still must be
    #       passed as a 2D list. The image is a heatmap of the FFT for that slice.
    # 'spec_time' is a list of numbers representing the 'time index' of a particular slice.
    #       This value is used to stack the images on top of each other, and is simply
    #       incremented whenever a slice is sent.

    # First plot a full spectrogram of nothing so new data is added proportionally.
    spectrogram_source.data = {
        'slice': [[[0]] for i in range(config['spectrogram_size'])],
        'spec_time': [i for i in range(config['spectrogram_size'])]
    }

    # create a spectrogram figure
    spec = figure(
        title="EEG Spectrogram",
        x_axis_label='Frequency (Hz)', y_axis_label='Time',
        plot_width=700, plot_height=500,
        toolbar_location=None
    )
    # image glyph
    spec_image = spec.image(
        image='slice',
        x=0, y='spec_time',
        dw=60, dh=1,
        source=spectrogram_source,
        color_mapper=mapper
    )
    spec.add_layout(color_bar, 'right')
    spec.background_fill_color = "black"
    spec.grid.visible = False

    ################
    # Head Plots
    # Load database of electrode placements
    # not used here yet, but I would like it to be
    with open('pages/electrodes.json', 'r') as f:
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
            plot_width=400, plot_height=400,
            toolbar_location=None
        )
        # Even though x and y don't change, they have to be gotten from the data source.
        # Each figure gets its own color mapper and takes
        #   data from the column with it's band name, which
        #   contains the color data.
        mapper = linear_cmap(field_name=band, palette='RdBu11', low=0, high=0.001)
        circle = fig.circle(x='x', y='y', source=headplot_source, color=mapper, size=20)
        fig.add_layout(color_bar, 'right')
        head_figures.append(fig)
        circles.append(circle)

    delta, theta, alpha, beta, gamma = head_figures  # delta, theta, alpha, beta, gamma
    delta_c, theta_c, alpha_c, beta_c, gamma_c = circles


    # Spectrogram color scale adjusting slider.
    # This needs to be here to get references to all the arguments for the CustomJS
    # None of the other widgets are in this function because they don't require references
    spectrogram_slider = RangeSlider(
        title="Scale",
        start=-10, end=1, step=1,  # log scale
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=config['spectrogram_range'])

    headplot_slider = RangeSlider(
        title="Scale",
        start=-10, end=1, step=1,  # log scale
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=config['spectrogram_range'])

    spectrogram_slider.js_on_change(
        "value",
        CustomJS(args=dict(  # arguments to be passed into the JS function
            image=spec_image,
            source=spectrogram_source,
            color_bar=color_bar,
            palette=palette,
        ),
            code="""
            var low = Math.pow(10, this.value[0]);
            var high = Math.pow(10, this.value[1]);
            if (low != high) {
                image.glyph.color_mapper.low = low;
                image.glyph.color_mapper.high = high;
                image.glyph.color_mapper.palette = palette;
                color_bar.color_mapper.low = low;
                color_bar.color_mapper.high = high;
                color_bar.color_mapper.palette = palette;
                source.change.emit();
            }
            """
        )
    )

    headplot_slider.js_on_change(
        "value",
        CustomJS(args=dict(  # arguments to be passed into the JS function
            color_bar=color_bar,
            palette=palette,
            source=headplot_source,
            delta=delta_c,
            theta=theta_c,
            alpha=alpha_c,
            beta=beta_c,
            gamma=gamma_c
        ),
        code="""
            var low = Math.pow(10, this.value[0]);
            var high = Math.pow(10, this.value[1]);
            if (low != high) {
                color_bar.color_mapper.low = low;
                color_bar.color_mapper.high = high;
                color_bar.color_mapper.palette = palette;
            
                var color_mapper = new Bokeh.LogColorMapper({palette:palette, low:low, high:high});
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

    # Tab for spectrogram has the range slider in it
    spec_tab = Panel(child=Row(spec, spectrogram_slider), title='Spectrogram')

    # Tab for
    head_tab = Panel(child=Column(Row(delta, theta, headplot_slider), Row(alpha, beta), Row(gamma)), title='Head Plots')  # create a tab for head plots

    #################
    # Construct final layout
    tabs = Tabs(tabs=[fourier_tab, head_tab])  # tabs object
    full_layout = layout([[eeg_list, [widgets_row, tabs]]])
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
    type = config[name+'_type']
    style = config[name+'_style']
    range = config[name+'_range']
    order = config[name+'_order']
    ripple = config[name+'_ripple']

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

