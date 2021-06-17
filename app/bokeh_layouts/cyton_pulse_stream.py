from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout


def create_layout(info):
    sample_rate = float(info['Raw']['sample_rate'])
    pulse_channels = info['Raw']['pulse_channels'].split(',')  # it's a comma separated string
    board_channels = info['Raw']['board_channels'].split(',')  # it's a comma separated string

    raw_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Raw']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=int(sample_rate*5),  # display last 5 seconds
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    hr_source = AjaxDataSource(
        data_url='/stream/update?id={}'.format(info['Heart Rate']['id']),
        method='GET',
        polling_interval=500,  # in milliseconds
        mode='append',  # append to existing data
        max_size=30,
        if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

    # Create Bokeh figures
    fig_list = []
    for i in range(len(board_channels)):
        fig = figure(
            title=board_channels[i],
            x_axis_label='time', y_axis_label='???',
            plot_width=600, plot_height=150,
            toolbar_location=None
        )
        fig.toolbar.active_drag = None
        fig.line(x='time', y=board_channels[i], source=raw_source)
        fig_list.append(fig)

    # Pulse figure
    pulse = figure(
        title='Pulse Sensor',
        x_axis_label='time', y_axis_label='Sensor Output',
        plot_width=600, plot_height=150,
        toolbar_location=None
    )
    pulse.toolbar.active_drag = None
    pulse.line(x='time', y=pulse_channels[0], source=raw_source)

    # Heart rate figure
    heart_rate = figure(
        title='Heart Rate',
        x_axis_label='time', y_axis_label='BPM',
        plot_width=600, plot_height=150,
        toolbar_location=None
    )
    heart_rate.toolbar.active_drag = None
    heart_rate.line(x='time', y='heart_rate', source=hr_source)

    # create layout
    return layout([[fig_list, [pulse, heart_rate]]])

