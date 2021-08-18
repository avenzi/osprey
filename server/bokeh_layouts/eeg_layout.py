from bokeh.models import CustomJS, AjaxDataSource
from bokeh.models import Panel, Tabs, ColorBar, LogColorMapper, LogTicker, PrintfTickFormatter
from bokeh.models import RangeSlider, Select, Spinner, Toggle, RadioButtonGroup
from bokeh.layouts import layout, Row
from bokeh.transform import log_cmap
from bokeh.plotting import figure
from bokeh.palettes import viridis, magma

from json import loads

from server.bokeh_layouts.utils import js_request, time_format, plot_sliding_js, plot_priority_js

BACKEND = 'canvas'  # 'webgl' appears to be broken - makes page unresponsive.

# default values of all widgets and figure attributes
default_filter_widgets = {
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
    'stop_order': 5,
    'stop_ripple': (1, 50),


}

default_fourier_widgets = {
    'fourier_window': 2,
    'spectrogram_range': (-3.0, 1.0),  # color scale range (log)
    'spectrogram_size': 30,

    'bands': {'Delta': (1, 4),
              'Theta': (4, 8),
              'Alpha': (8, 12),
              'Beta': (12, 30),
              'Gamma': (30, 100)}
}


def create_layout(info):
    """
    Configures all Bokeh figures and plots
    <info> dict. keys are stream names assigned in this group.
        Values are dictionaries of the info given to that stream.
    """
    # TODO: Split this up into more easily digestible chunks?
    # TODO: Remove Spectrogram for good. Too much data is required to make it worth while,
    #  and it's not necessary because of the headplots. Will need to remove the AjaxDataSource,
    #  spectrogram image and figure creation, the JS callback from the radio buttons targetting the
    #  spec images, the spectrogram Tab creation, and the code adding/sending data to the browser in
    #  the EEGHandler class. It's a good example of how to do a spectrogram in Bokeh, though, so
    #  I may want to keep it somewhere as a reference for later.
    # get channel names
    stream_channels = info['Raw']['channels'].split(',')  # it's a comma separated string
    sample_rate = float(info['Raw']['sample_rate'])

    # get stream IDs
    filtered_id = info['Filtered']['id']  # Filter Analyzer ID
    fourier_id = info['Fourier']['id']  # Fourier Analyzer ID
    transformed_id = info['Transformed']['id']  # Transform Analyzer ID

    # get filter widget values
    filter_widgets = info['Filtered'].get('widgets')
    if filter_widgets:  # config present, it's a JSON string.
        filter_widgets = loads(filter_widgets)
    else:  # no config present, use default
        filter_widgets = default_filter_widgets

    # get fourier widget values
    fourier_widgets = info['Fourier'].get('widgets')
    if fourier_widgets:  # if config present, it's a JSON string.
        fourier_widgets = loads(fourier_widgets)
    else:  # no config present, use default
        fourier_widgets = default_fourier_widgets

    # viridis color palette for channel colors
    colors = viridis(len(stream_channels))

    ##########################
    # create row of widgets that send data to the analyzer streams
    # Fourier Window sliders
    fourier_window = Spinner(title="FFT Window (s)", low=1, high=10, step=1, width=90, value=fourier_widgets['fourier_window'])
    fourier_window.js_on_change("value", CustomJS(code=js_request(fourier_id, 'fourier_window')))

    # Toggle buttons
    pass_toggle = Toggle(label="Bandpass", button_type="success", width=100, margin=(24, 5, 0, 5), active=filter_widgets['pass_toggle'])
    pass_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'pass_toggle', 'active')))

    stop_toggle = Toggle(label="Bandstop", button_type="success", width=100, margin=(24, 5, 0, 5), active=filter_widgets['stop_toggle'])
    stop_toggle.js_on_click(CustomJS(code=js_request(filtered_id, 'stop_toggle', 'active')))

    # Range sliders. "value_throttled" only takes the slider value once sliding has stopped
    pass_range = RangeSlider(title="Range", start=0.1, end=100, step=0.1, value=filter_widgets['pass_range'])
    pass_range.js_on_change("value_throttled", CustomJS(code=js_request(filtered_id, 'pass_range')))

    stop_range = RangeSlider(title="Range", start=40, end=70, step=0.5, value=filter_widgets['stop_range'])
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
    eeg_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(filtered_id),
        method='GET',
        polling_interval=1000,
        mode='append',
        max_size=int(sample_rate*10),
        if_modified=True)

    eeg_transformed_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format('Filtered:'+transformed_id),
        method='GET',
        polling_interval=1000,
        mode='append',
        max_size=int(sample_rate*10),
        if_modified=True)

    fourier_source = AjaxDataSource(
        data_url='/stream/update?id=fourier:{}&format=snapshot'.format(fourier_id),
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
        data_url='/stream/update?id=headplot:{}&format=snapshot'.format(fourier_id),
        method='GET',
        polling_interval=1000,
        mode='replace',
        if_modified=True)

    #############################################
    # create EEG figure with all EEG lines plotted on it
    # initial x_range must be set in order to disable auto-scaling
    # initial y_ranges should not be set to enable auto-scaling
    eeg = figure(
        title='EEG Channels',
        x_axis_label='Time (s)', y_axis_label='Voltage (uV)',
        plot_width=1200, plot_height=200,
        toolbar_location=None,
        output_backend=BACKEND
    )
    eeg.xaxis.formatter = time_format()
    eeg.toolbar.active_drag = None  # disable drag

    # y-axis range will autoscale to currently selected channel
    eeg.y_range.only_visible = True

    for i in range(len(stream_channels)):  # plot each line
        visible = True if i == 0 else False  # first channel visible
        eeg.line(x='time', y=stream_channels[i], name=stream_channels[i], color=colors[i], source=eeg_source, visible=visible)
        # transformed line
        eeg.line(x='time', y=stream_channels[i], name=stream_channels[i]+'_transformed', color=colors[i], source=eeg_transformed_source, visible=visible)

    plot_sliding_js(eeg, eeg_source)  # incoming data smoothing
    plot_priority_js(eeg, back_source=eeg_source, front_source=eeg_transformed_source)  # give transformed data priority

    # fourier figure with a line for each EEG channel
    fourier = figure(
        title="EEG Fourier",
        x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log",
        plot_width=1200, plot_height=400,
        tools='xpan,xwheel_zoom,reset', toolbar_location='above',
        output_backend=BACKEND
    )

    for i in range(len(stream_channels)):
        fourier.line(x='frequencies', y=stream_channels[i], color=colors[i], source=fourier_source)
    fourier_panel = Panel(child=fourier, title='FFT')  # create a tab for this plot

    ################
    # Color mapper for the headplot ColorBar
    mapper_low = 10 ** (fourier_widgets['spectrogram_range'][0])  # low threshold
    mapper_high = 10 ** (fourier_widgets['spectrogram_range'][1])  # high threshold
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

    # Radio buttons to select channels on the EEG figure figure
    channel_radios = RadioButtonGroup(labels=stream_channels, active=0)
    channel_radios.js_on_click(CustomJS(
        args=dict(
            eeg_fig=eeg,
            labels=stream_channels
        ),
        code="""
    eeg_fig.select_one(this.labels[this.active]).visible = true
    eeg_fig.select_one(this.labels[this.active]+'_transformed').visible = true  // transformed
    // spec_fig.select_one(this.labels[this.active]).visible = true (to remove)
    for (var label of labels) {
        if (label != this.labels[this.active]){
            eeg_fig.select_one(label).visible = false
            eeg_fig.select_one(label+'_transformed').visible = false
            // spec_fig.select_one(label).visible = false (to remove)
        }
    }
    """))

    ################
    # Head Plots

    # tooltip to display channel name on headplot
    headplot_tooltips = [
        ("Channel", "@channel"),
    ]

    # Separate head figure for each band
    head_figures = []  # list of headplot figures
    circles = []  # list of circle glyphs used to update the color mapping
    for band in fourier_widgets['bands']:
        fig = figure(
            title='{}-band Head Plot'.format(band),
            plot_width=300, plot_height=300,
            toolbar_location=None, tooltips=headplot_tooltips,
            output_backend=BACKEND
        )
        fig.toolbar.active_drag = None  # disable drag
        fig.toolbar.active_scroll = None
        # Even though x and y of each point don't change, they have to be gotten from the data source.
        # Each figure gets its own color mapper and takes data from the
        #   column with it's band name, which contains the color data.
        mapper = log_cmap(field_name=band, palette=mapper_palette, low=mapper_low, high=mapper_high)
        circle = fig.circle(x='x', y='y', source=headplot_source, color=mapper, size=20)
        fig.xaxis.ticker, fig.yaxis.ticker = [], []  # disable axes
        head_figures.append(fig)
        circles.append(circle)

    delta, theta, alpha, beta, gamma = head_figures  # figures
    delta_c, theta_c, alpha_c, beta_c, gamma_c = circles  # glyphs

    # put colorbar on left-most plot and increase width to accommodate
    delta.add_layout(color_bar, 'left')
    delta.plot_width = 390  # this seems to be the right amount visually

    # Headplot color scale adjusting slider.
    # This widget needs to be here (as opposed to at the top with all the other widgets) because
    # it needs to get references to all the arguments for the CustomJS.
    # None of the other widgets are in this function because they don't require references.
    headplot_slider = RangeSlider(
        title='',
        start=-10, end=3, step=1,  # log scale
        orientation='vertical',
        direction='rtl',  # Right to left, but vertical so top to bottom
        value=fourier_widgets['spectrogram_range'])

    # TODO: The colorbar is not updating in the plot. The circle glyphs are updating just fine,
    #  but no matter what I try the colorbar doesn't change its color range or tickmarks.

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

