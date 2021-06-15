from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout


def create_layout(info):
    source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Sense']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 100 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    humid = figure(title='Humidity', x_axis_label='time', y_axis_label='Percent', toolbar_location=None, plot_width=600, plot_height=300)
    humid.toolbar.active_drag = None
    humid.line(x='time', y='humidity', source=source)

    press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', toolbar_location=None, plot_width=600, plot_height=300)
    press.toolbar.active_drag = None
    press.line(x='time', y='pressure', source=source)

    temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', toolbar_location=None, plot_width=600, plot_height=300)
    temp.toolbar.active_drag = None
    temp.line(x='time', y='temperature', source=source)

    orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', toolbar_location=None, plot_width=600, plot_height=300)
    orient.toolbar.active_drag = None
    orient.line(x='time', y='pitch', legend_label='Pitch', color='blue', source=source)
    orient.line(x='time', y='roll', legend_label='Roll', color='green', source=source)
    orient.line(x='time', y='yaw', legend_label='Yaw', color='red', source=source)

    # create layout
    return layout([[humid, temp], [press, orient]])
