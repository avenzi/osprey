from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout

from server.bokeh_layouts.utils import time_format, plot_sliding_js


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
    plot_sliding_js(humid, source)

    press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', toolbar_location=None, plot_width=600, plot_height=250)
    press.xaxis.formatter = time_format()
    press.toolbar.active_drag = None
    press.line(x='time', y='pressure', source=source)
    plot_sliding_js(press, source)

    temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', toolbar_location=None, plot_width=600, plot_height=250)
    temp.xaxis.formatter = time_format()
    temp.toolbar.active_drag = None
    temp.line(x='time', y='temperature', source=source)
    plot_sliding_js(temp, source)

    orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', toolbar_location=None, plot_width=600, plot_height=250)
    orient.xaxis.formatter = time_format()
    orient.toolbar.active_drag = None
    orient.line(x='time', y='pitch', legend_label='Pitch', color='blue', source=source)
    orient.line(x='time', y='roll', legend_label='Roll', color='green', source=source)
    orient.line(x='time', y='yaw', legend_label='Yaw', color='red', source=source)
    plot_sliding_js(orient, source)

    tooltips = [
        ('Button', '@button'),
        ('Time', '@time')
    ]

    buttons = figure(title='Button Presses', tooltips=tooltips, x_axis_label='time', y_axis_label='', y_range=(0,1), toolbar_location=None, plot_width=1200, plot_height=100)
    buttons.xaxis.formatter = time_format()
    buttons.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    buttons.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks
    buttons.yaxis.major_label_text_font_size = '0pt'  # turn off y-axis tick labels
    buttons.toolbar.active_drag = None
    buttons.segment(x0='time', x1='time', y0=-1, y1=1, source=button_source, line_color='color', line_width=10)
    buttons.line(x='time', y=0, source=source, color='black', visible=False)

    # create layout
    return layout([[humid, temp], [press, orient], [buttons]])
