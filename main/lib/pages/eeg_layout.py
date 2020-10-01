from bokeh.models import CustomJS, AjaxDataSource
from bokeh.models import Panel, Tabs, ColorBar, LogColorMapper, LogTicker
from bokeh.models import Slider, RangeSlider, Select, Spinner, Toggle
from bokeh.layouts import layout, Row, Column
from bokeh.plotting import figure
from bokeh.palettes import viridis, magma

from scipy import signal


# default values of all widgets and figure attributes
config = {'fourier_window': 5,
          'spectrogram_range': (-9.0, -2.0),
          'spectrogram_size': 30,
          'filter_toggle': True,
          'filter_type': 'Bandpass',
          'filter_style': 'Butterworth',
          'filter_range': (5, 62),
          'filter_order': 3,
          'filter_ripple': (1, 50),
          'notch_toggle': True,
          'notch_center': 60,
          'notch_order': 3
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
        console.log(json.length);
        req.send(json);
        console.log('{key}: ' + this.{attribute});
    """
    return code.format(path=widget_path, key=key, attribute=attribute)


# Fourier Window sliders
fourier_window = Slider(title="FFT Window (seconds)", start=0, end=20, step=1, value=config['fourier_window'])
fourier_window.js_on_change("value_throttled", CustomJS(code=js_request('fourier_window')))

# Toggle buttons
filter_toggle = Toggle(label="Filter", button_type="success", active=config['filter_toggle'])
filter_toggle.js_on_click(CustomJS(code=js_request('filter_toggle', 'active')))

notch_toggle = Toggle(label="Notch", button_type="success", active=config['notch_toggle'])
notch_toggle.js_on_click(CustomJS(code=js_request('notch_toggle', 'active')))

# Range slider and Center/Width sliders
filter_range = RangeSlider(title="Range", start=0, end=70, step=1, value=config['filter_range'])
filter_range.js_on_change("value_throttled", CustomJS(code=js_request('filter_range')))

notch_center = Slider(title="Center", start=0, end=60, step=1, value=config['notch_center'])
notch_center.js_on_change("value_throttled", CustomJS(code=js_request('notch_center')))

# Filter selectors
filter_style = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=config['filter_style'])
filter_style.js_on_change("value", CustomJS(code=js_request('filter_style')))

# Order spinners
filter_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=config['filter_order'])
filter_order.js_on_change("value", CustomJS(code=js_request('filter_order')))

notch_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=config['notch_order'])
notch_order.js_on_change("value", CustomJS(code=js_request('notch_order')))

# Used to construct the Bokeh layout of widgets
widgets_row = [[[filter_toggle, filter_style, filter_order], filter_range,
               [notch_toggle, notch_order], notch_center, fourier_window]]


# Bokeh Figures
def configure_layout(worker_id, channels):
    """
    Configures all Bokeh figures and plots
    :param worker_id: Id of the WorkerNode (just self.id)
    :param channels: List of EEG channels being plotted.
    :return:
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

    # Spectrogram color scale adjusting slider.
    # This needs to be here to get references to all the arguments for the CustomJS
    # None of the other widgets are in this function because they don't require references
    spectrogram_slider = RangeSlider(
        title="Scale",
        start=-10, end=1, step=1,
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=config['spectrogram_range'])

    spectrogram_slider.js_on_change(
        "value",
        CustomJS(args=dict(  # arguments to be passed into the JS function
            image=spec_image,
            source=spectrogram_source,
            color_bar=color_bar,
            palette=palette),
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
    # Tab for spectrogram has the range slider in it
    spec_tab = Panel(child=Row(spec, spectrogram_slider), title='Spectrogram')

    # Construct final layout

    tabs = Tabs(tabs=[fourier_tab, spec_tab])  # tabs object
    full_layout = layout([[eeg_list, [widgets_row, tabs]]])
    return full_layout


def create_sos(sample_rate, config):
    """
    Returns the Second Order Sections of the given filter design.
    [sample rate] int: Number of samples per second
    [config] dict: Configuration dictionary seen at the top of this file. Must contain:
        [filter_type] string: bandpass, lowpass, highpass
        [filter_style] string: Bessel, Butterworth, Chebyshev 1, Chebyshev 2, Elliptic
        [crit] tuple: (low, high) critical values for the filter cutoffs
        [order] int: Order of filter polynomial
        [ripple] tuple: (max gain, max attenuation) for chebyshev and elliptic filters
    """
    type = config['filter_type']
    style = config['filter_style']
    range = config['filter_range']
    order = config['filter_order']
    ripple = config['filter_ripple']

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
