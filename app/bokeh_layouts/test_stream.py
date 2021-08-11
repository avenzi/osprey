from bokeh.plotting import figure
from bokeh.models import AjaxDataSource, CustomJS
from bokeh.layouts import layout

from app.bokeh_layouts.utils import time_format, plot_sliding_js, plot_priority_js


def create_stream_layout(info):
    source1 = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Random 1']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=500,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    source2 = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Random 2']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=500,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    # at the moment, the transform source only modifies the data in Random 2
    transform_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Transformed']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=500,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    data1 = figure(title='Sample Data 1', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data1.xaxis.formatter = time_format()
    data1.toolbar.active_drag = None
    data1.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source1)
    data1.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source1)
    data1.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source1)
    plot_sliding_js(data1, source1)  # incoming data smoothing

    data2 = figure(title='Sample Data 2', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data2.xaxis.formatter = time_format()
    data2.toolbar.active_drag = None
    data2.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source2)
    data2.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source2)
    data2.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source2)
    # same lines but from the transformed source
    data2.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=transform_source)
    data2.line(x='time', y='val_2', legend_label='Val 2', color='green', source=transform_source)
    data2.line(x='time', y='val_3', legend_label='Val 3', color='red', source=transform_source)
    plot_sliding_js(data2, source2)  # incoming data smoothing
    plot_priority_js(data2, back_source=source2, front_source=transform_source)  # give transformed data priority

    # create layout
    return layout([[data1, data2]])  # format into layout object


def create_analyzer_layout(info):
    # Need a separate data source for each line because the data can all be different lengths
    source11 = AjaxDataSource(
        data_url='/stream/update?id=11:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source12 = AjaxDataSource(
        data_url='/stream/update?id=12:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source21 = AjaxDataSource(
        data_url='/stream/update?id=21:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source22 = AjaxDataSource(
        data_url='/stream/update?id=22:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    data = figure(title='Averages', x_axis_label='time', y_axis_label='Average Value', toolbar_location=None, plot_width=600, plot_height=300)
    data.xaxis.formatter = time_format()
    data.toolbar.active_drag = None
    data.line(x='time', y='data', legend_label='Data 11', color='blue', source=source11)
    data.line(x='time', y='data', legend_label='Data 12', color='green', source=source12)
    data.line(x='time', y='data', legend_label='Data 21', color='red', source=source21)
    data.line(x='time', y='data', legend_label='Data 22', color='yellow', source=source22)

    return layout(data)  # format into layout object
