from bokeh.plotting import figure
from bokeh.models import AjaxDataSource, CustomJS
from bokeh.layouts import layout

from app.bokeh_layouts.utils import time_format


def create_layout(info):
    source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Raw']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=1000,  # Keep last 100 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    button_source = AjaxDataSource(
        data_url='/stream/update?id=button:{}'.format(info['Raw']['id']),
        method='GET',
        polling_interval=1000,  # in milliseconds
        mode='append',  # append to existing data
        max_size=20,  # Keep last 10 data points
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    humid = figure(title='Humidity', x_axis_label='time', y_axis_label='Percent', toolbar_location=None, plot_width=600, plot_height=250)
    humid.xaxis.formatter = time_format()
    humid.toolbar.active_drag = None
    humid.line(x='time', y='humidity', source=source)

    press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', toolbar_location=None, plot_width=600, plot_height=250)
    press.xaxis.formatter = time_format()
    press.toolbar.active_drag = None
    press.line(x='time', y='pressure', source=source)

    temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', toolbar_location=None, plot_width=600, plot_height=250)
    temp.xaxis.formatter = time_format()
    temp.toolbar.active_drag = None
    temp.line(x='time', y='temperature', source=source)

    orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', toolbar_location=None, plot_width=600, plot_height=250)
    orient.xaxis.formatter = time_format()
    orient.toolbar.active_drag = None
    orient.line(x='time', y='pitch', legend_label='Pitch', color='blue', source=source)
    orient.line(x='time', y='roll', legend_label='Roll', color='green', source=source)
    orient.line(x='time', y='yaw', legend_label='Yaw', color='red', source=source)

    button = figure(title='Button Presses', x_axis_label='time', y_axis_label='', toolbar_location=None, plot_width=1200, plot_height=100)
    button.xaxis.formatter = time_format()
    button.toolbar.active_drag = None
    button.circle(x='time', y=0, source=button_source, size=30, fill_color='color', line_width=0)
    button.line(x='time', y=0, source=source, color='black')

    # create layout
    return layout([[humid, temp], [press, orient], [button]])
