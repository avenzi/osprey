from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout

from server.bokeh_layouts.utils import time_format, plot_sliding_js, plot_priority_js


def create_layout(info):
    source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Decoded Audio']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=500,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    transformed_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Transformed Audio']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=500,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    fig = figure(title='Audio Waveform', x_axis_label='time', y_axis_label='value', toolbar_location=None, plot_width=1200, plot_height=300)
    fig.xaxis.formatter = time_format()
    fig.toolbar.active_drag = None
    fig.line(x='time', y='data', color='blue', source=source)
    fig.line(x='time', y='data', color='blue', source=transformed_source)
    plot_sliding_js(fig, source)  # incoming data smoothing
    plot_priority_js(fig, back_source=source, front_source=transformed_source)  # give transformed data priority

    # create layout
    return layout([fig])  # format into layout object