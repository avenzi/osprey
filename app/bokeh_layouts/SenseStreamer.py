from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout
from bokeh.embed import json_item
import json

source = AjaxDataSource(
    data_url='/update?name={}'.format('SenseStreamer'),
    method='GET',
    polling_interval=100,  # in milliseconds
    mode='append',  # append to existing data
    max_size=100,  # Keep last 1000 data points
    if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

humid = figure(title='Humidity', x_axis_label='time', y_axis_label='Percent', toolbar_location=None, plot_width=600, plot_height=300)
humid.line(x='time', y='humidity', source=source)
press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', toolbar_location=None, plot_width=600, plot_height=300)
press.line(x='time', y='pressure', source=source)
temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', toolbar_location=None, plot_width=600, plot_height=300)
temp.line(x='time', y='temperature', source=source)
orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', toolbar_location=None, plot_width=600, plot_height=300)
orient.line(x='time', y='pitch', legend_label='Pitch', color='blue', source=source)
orient.line(x='time', y='roll', legend_label='Roll', color='green', source=source)
orient.line(x='time', y='yaw', legend_label='Yaw', color='red', source=source)

# create layout
lay = layout([[humid, temp], [press, orient]])
