from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout


def create_layout(info):
    source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    source2 = AjaxDataSource(
        data_url='/stream/update?id=multiplied:{}'.format(info['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 1000 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    data = figure(title='Sample Data', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source)
    data.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source)
    data.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source)

    data2 = figure(title='Transformed Data', x_axis_label='time', y_axis_label='Data', toolbar_location=None, plot_width=600, plot_height=300)
    data2.line(x='time', y='val_1', legend_label='Val 1', color='blue', source=source2)
    data2.line(x='time', y='val_2', legend_label='Val 2', color='green', source=source2)
    data2.line(x='time', y='val_3', legend_label='Val 3', color='red', source=source2)

    # create layout
    return layout([data, data2])  # format into layout object
