from bokeh.layouts import layout
from bokeh.plotting import figure
from bokeh.palettes import viridis
from bokeh.models import AjaxDataSource

# EEG Bokeh widgets
from pages.eeg_widgets import widgets, widgets_row, fourier_window

import numpy as np
import json

from server_lib import Handler, GraphStream
from lib import Request, Response, DataBuffer, GraphRingBuffer


class VideoHandler(Handler):
    """ Handles video stream """
    def __init__(self):
        super().__init__()

        self.framerate = None
        self.resolution = None
        self.max_display_height = 600   # maximum height of video in browser

        self.frames_sent = 0
        self.frames_received = 0

        self.image_buffer = DataBuffer()

    def INIT(self, request):
        """ Handles INIT request from client """
        self.framerate = request.header['framerate']
        self.resolution = tuple(int(res) for res in request.header['resolution'].split('x'))

    def INGEST(self, request):
        """ Handle image data received from Pi """
        frame = request.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(request.header['frames-sent'])
        self.image_buffer.write(frame)  # raw data needs no modification - it's already an image
        self.debug("ingested video", 3)

    def GET(self, request):
        """
        Returns response object for a GET request
        Return False to fall back to general server response
        """
        if request.path.endswith('/stream'):  # request for data stream page html
            response = Request()
            response.add_response(200)
            response.add_header('content-type', 'text/html')
            response.add_content(self.page_html())
            self.send(response, request.origin)
        elif request.path.endswith('/stream.mjpg'):  # request for an mjpg
            request.origin.send_multipart(self.image_buffer)
        else:
            self.debug("Path not recognized: {}".format(request.path), 2)

    def page_html(self):
        """ Returns HTML for streaming display page in browser """
        aspect = self.resolution[0] / self.resolution[1]
        height = self.max_display_height
        width = int(aspect * height)
        update_url = '/stream.mjpg?id={}'.format(self.id)
        page = """
                <html>
                <head><title>{name}</title></head>
                <body>
                    <h1>{name}</h1>
                    <p><a href='/index.html'>Back</a></p>
                    <p><img src="{url}" width="{width}" height="{height}" /></p>
                </body>
                </html>
                """.format(name=self.name, url=update_url, width=width, height=height)
        return page


class SenseHandler(Handler):
    """ Handles SenseHat stream """
    def __init__(self):
        super().__init__()

        self.frames_sent = 0
        self.frames_received = 0

        # Create Bokeh figures
        source = AjaxDataSource(
            data_url='/update?id={}'.format(self.id),
            method='GET',
            polling_interval=100,  # in milliseconds
            mode='append',         # append to existing data
            max_size=100,          # Keep last 1000 data points
            if_modified=True)      # if_modified ignores responses sent with code 304 and not cached.

        tools = ['save']
        humid = figure(title='Humidity', x_axis_label='time', y_axis_label='Percent', tools=tools, plot_width=600, plot_height=300)
        humid.line(x='time', y='humidity', source=source)
        press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', tools=tools, plot_width=600, plot_height=300)
        press.line(x='time', y='pressure', source=source)
        temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', tools=tools, plot_width=600, plot_height=300)
        temp.line(x='time', y='temperature', source=source)
        orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', tools=tools, plot_width=600, plot_height=300)
        orient.line(x='time', y='pitch', legend_label='Pitch', color='blue', source=source)
        orient.line(x='time', y='roll', legend_label='Roll', color='green', source=source)
        orient.line(x='time', y='yaw', legend_label='Yaw', color='red', source=source)

        # create layout
        lay = layout([[humid, temp], [press, orient]])
        # pass layout into GraphStream object, polling interval in ms, domain of x values to display
        self.graph = GraphStream(lay)

        self.buffer = DataBuffer()
        self.buffer_lock = self.buffer.get_read_lock()

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(request.encoding)  # raw JSON string
        self.buffer.write(data)  # save raw JSON string in buffer.
        self.frames_received += 1
        self.debug("Ingested sense data (frame {})".format(self.frames_received), 3)

    def GET(self, request):
        """
        Returns response object for a GET request
        Return False to fall back to general server response
        """
        if request.path.endswith('/stream'):  # request for data stream page html
            response = self.graph.stream_page()
        elif request.path.endswith('/plot'):  # request for initial plot JSON
            response = self.graph.plot_json()
        elif request.path.endswith('/update'):  # request for data stream update
            response = self.graph.update_json(self.buffer, self.buffer_lock)
        else:
            self.debug("Path not recognized: {}".format(request.path), 2)
            return
        self.send(response, request.origin)


class EEGHandler(Handler):
    """ Handles SenseHat stream """
    def __init__(self):
        super().__init__()

        self.frames_sent = 0
        self.frames_received = 0
        self.channels = []  # list of channel name strings
        self.sample_rate = 0  # sampling rate of EEG data

        # need a list of channel names, so most of these are initialized in the INIT method
        self.graph = None

        self.eeg_buffer = None
        self.eeg_lock = None  # ticket to read from EEG buffer

        self.fourier_buffer = None
        self.fourier_lock = None  # ticket to read latest data from Fourier buffer
        self.fourier_all_lock = None  # ticket to read all data from fourier buffer at once

        # dictionary of values for all widgets, imported from /pages/eeg_widgets
        self.widgets = widgets

    def INIT(self, request):
        """ Handles INIT request from client """
        self.channels = request.header['channels'].split(',')  # list of EEG channel names
        self.sample_rate = float(request.header['sample_rate'])  # data points per second

        # Bokeh configuration
        tools = ['save']
        colors = viridis(len(self.channels))  # viridis color palette

        # create AJAX data sources for the plots
        eeg_source = AjaxDataSource(
            data_url='/update_eeg?id={}'.format(self.id),
            method='GET',
            polling_interval=200,
            mode='append',
            max_size=1000,
            if_modified=True)
        fourier_source = AjaxDataSource(
            data_url='/update_fourier?id={}'.format(self.id),
            method='GET',
            polling_interval=2000,
            mode='replace',
            if_modified=True)

        # create EEG figures, each with it's own line
        eeg_list = []
        for i in range(len(self.channels)):
            eeg = figure(title=self.channels[i], x_axis_label='time', y_axis_label='Voltage', tools=tools, plot_width=600, plot_height=150)
            eeg.line(x='time', y=self.channels[i], color=colors[i], source=eeg_source)
            eeg_list.append(eeg)

        # Create fourier figure with a line for each EEG channel
        fourier = figure(
            title="EEG Fourier", x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log", tools=tools, plot_width=700, plot_height=500)
        for i in range(len(self.channels)):
            fourier.line(x='frequencies', y=self.channels[i]+'_fourier', color=colors[i], source=fourier_source)

        # Create layout and pass into GraphStream object
        # widgets_row and fourier_window imported from /pages/eeg_widgets
        lay = layout([[eeg_list, [widgets_row, fourier_window, fourier]]])
        self.graph = GraphStream(lay)

        # size of EEG buffer (# of data points to keep). FFT window is in seconds, sample rate is data points per second.
        size = int(widgets['fourier_window'] * self.sample_rate)

        self.eeg_buffer = GraphRingBuffer(self.channels, size)
        self.eeg_lock = self.eeg_buffer.get_read_lock()

        self.fourier_buffer = DataBuffer()
        self.fourier_lock = self.fourier_buffer.get_read_lock()
        self.fourier_all_lock = self.fourier_buffer.get_read_lock()

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(request.encoding)  # raw JSON data
        data = json.loads(data)  # load into a dictionary
        self.filter(data)
        self.denoise(data)
        self.eeg_buffer.write(data)  # write data to EEG buffer
        self.frames_received += 1
        self.debug("Ingested EEG data (frame {})".format(self.frames_received), 3)

    def GET(self, request):
        """ Handles a GET request send to the handler """
        if request.path.endswith('/stream'):  # request for data stream page html
            response = self.graph.stream_page()
        elif request.path.endswith('/plot'):  # request for initial plot JSON
            response = self.graph.plot_json()
        elif request.path.endswith('/update_eeg'):  # request for eeg stream update
            response = self.graph.update_json(self.eeg_buffer, self.eeg_lock)  # get update from EEG buffer
        elif request.path.endswith('/update_fourier'):  # request for fourier update
            self.fourier()  # perform FFT
            response = self.graph.update_json(self.fourier_buffer, self.fourier_lock)  # get update from fourier buffer
        elif request.path.endswith('/widgets'):  # A widget was updated
            header, value = list(request.header.items())[0]  # only one header should be sent
            if header in ['bandpass_toggle', 'bandstop_toggle']:  # JS bools
                if value == 'false':  # I am ashamed that I have to do this
                    value = False
                if value == 'true':
                    value = True
            elif header in ['bandpass_range']:  # range slider gives comma-separated values
                value = tuple(float(i) for i in value.split(','))
            elif header in ['bandpass_order', 'bandstop_order', 'fourier_window']:
                value = int(value)  # ints
            elif header in ['bandstop_center', 'bandstop_width']:
                value = float(value)  # floats
            # band pass/stop filter type is already a string

            self.widgets[header] = value
            response = Response(204)  # no content successful response
        else:
            self.debug("Path not recognized: {}".format(request.path), 2)
            return
        self.send(response, request.origin)

    def filter(self, data):
        """ Performs frequency filters on the input dictionary of data in-place"""
        # for demo apply different filters to different channels, in production choose one
        '''
        for name, data in data.items():
            # filters work in-place
            if count == 0:
                DataFilter.perform_bandpass(data[channel], BoardShim.get_sampling_rate(board_id), 15.0, 6.0, 4, FilterTypes.BESSEL.value, 0)
            elif count == 1:
                DataFilter.perform_bandstop(data[channel], BoardShim.get_sampling_rate(board_id), 30.0, 1.0, 3, FilterTypes.BUTTERWORTH.value, 0)
            elif count == 2:
                DataFilter.perform_lowpass(data[channel], BoardShim.get_sampling_rate(board_id), 20.0, 5, FilterTypes.CHEBYSHEV_TYPE_1.value, 1)
            elif count == 3:
                DataFilter.perform_highpass(data[channel], BoardShim.get_sampling_rate(board_id), 3.0, 4, FilterTypes.BUTTERWORTH.value, 0)
            '''
    def denoise(self, data):
        """ Performs de-noising algorithms on the input dictionary of data in-place """
        return

    def fourier(self):
        """ Calculates the FFT from all EEG data available """
        data = self.eeg_buffer.read_all(self.fourier_all_lock)  # dict of all current data
        fourier_dict = {name+'_fourier': [] for name in self.channels}
        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        freqs = np.fft.fftfreq(N, 1/self.sample_rate)[:N//2]  # frequency array
        fourier_dict['frequencies'] = freqs.tolist()  # numpy types are not JSON serializable
        for name, channel_data in data.items():
            fft = (np.fft.fft(channel_data)[:N//2])/N  # half frequency range and normalize
            fft = np.sqrt(np.real(fft)**2 + np.imag(fft)**2)
            fourier_dict[name+'_fourier'] = fft.tolist()  # numpy types are not JSON serializable
        fourier_json = json.dumps(fourier_dict)
        self.fourier_buffer.write(fourier_json)





