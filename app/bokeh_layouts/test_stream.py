from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout


def create_stream_layout(info):
    source1 = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Random 1']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    source2 = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Random 2']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    data1 = figure(title='Sample Data 1', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data1.toolbar.active_drag = None
    data1.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source1)
    data1.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source1)
    data1.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source1)

    data2 = figure(title='Sample Data 2', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data2.toolbar.active_drag = None
    data2.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source2)
    data2.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source2)
    data2.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source2)

    # create layout
    return layout([[data1, data2]])  # format into layout object


def create_analyzer_layout(info):
    # Need a separate data source for each line because the data can all be different lengths
    source11 = AjaxDataSource(
        data_url='/stream/update?id=11:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source12 = AjaxDataSource(
        data_url='/stream/update?id=12:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source21 = AjaxDataSource(
        data_url='/stream/update?id=21:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.
    source22 = AjaxDataSource(
        data_url='/stream/update?id=22:{}'.format(info['Random Analyzer']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    data = figure(title='Averages', x_axis_label='time', y_axis_label='Average Value', toolbar_location=None, plot_width=600, plot_height=300)
    data.toolbar.active_drag = None
    data.line(x='time_11', y='data_11', legend_label='Data 11', color='blue', source=source11)
    data.line(x='time_12', y='data_12', legend_label='Data 12', color='green', source=source12)
    data.line(x='time_21', y='data_21', legend_label='Data 21', color='red', source=source21)
    data.line(x='time_22', y='data_22', legend_label='Data 22', color='yellow', source=source22)

    return layout(data)  # format into layout object
