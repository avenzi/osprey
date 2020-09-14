from bokeh.layouts import layout
from bokeh.plotting import figure
from bokeh.palettes import viridis
from bokeh.models import AjaxDataSource, CustomJS, RangeSlider, Button

import numpy as np
import json

from server_lib import Handler, GraphStream, GraphRingBuffer
from lib import Request, Response, DataBuffer


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
        self.min_freq = 0  # minimum frequency
        self.max_freq = 0  # maximum frequency

        # A list of channel names is required, so self.graph is initialized in the INIT method
        self.graph = None

        self.eeg_buffer = None
        self.eeg_lock = None

        self.fourier_buffer = None
        self.fourier_lock = None
        self.fourier_all_lock = None

    def INIT(self, request):
        """ Handles INIT request from client """
        self.channels = request.header['channels'].split(',')
        self.sample_rate = float(request.header['sample_rate'])
        self.min_freq, self.max_freq = 0, self.sample_rate//2

        tools = ['save']
        colors = viridis(len(self.channels))  # viridis color palette

        # create data sources
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
        fourier = figure(title="EEG Fourier", x_axis_label='Frequency (Hz)', y_axis_label='Magnitude (log)', y_axis_type="log", tools=tools, plot_width=700, plot_height=500)
        for i in range(len(self.channels)):
            fourier.line(x='frequencies', y=self.channels[i]+'_fourier', color=colors[i], source=fourier_source)

        # Fourier Filter Slider
        filter_slider = RangeSlider(start=self.min_freq, end=self.max_freq, value=(self.min_freq, self.max_freq), step=1, title="Frequency Filter")
        filter_slider.js_on_change("value", CustomJS(code="""
            var req = new XMLHttpRequest();
            url = window.location.pathname
            queries = window.location.search
            req.open("GET", url+'/filter_slider'+queries, true);
            req.setRequestHeader('values', this.value)  // tuple
            req.send(null);
            console.log('range_slider: value=' + this.value, this.toString())
        """))

        # Create layout and pass into GraphStream object
        lay = layout([[eeg_list, [fourier, filter_slider]]])
        self.graph = GraphStream(lay)

        self.eeg_buffer = GraphRingBuffer(self.channels, 1000)
        self.eeg_lock = self.eeg_buffer.get_read_lock()

        self.fourier_buffer = DataBuffer()
        self.fourier_lock = self.fourier_buffer.get_read_lock()
        self.fourier_all_lock = self.fourier_buffer.get_read_lock()

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(request.encoding)  # raw JSON data
        self.eeg_buffer.write(data)
        self.frames_received += 1
        self.debug("Ingested EEG data (frame {})".format(self.frames_received), 3)

    def GET(self, request):
        """
        Handles a GET request send to the handler
        """
        if request.path.endswith('/stream'):  # request for data stream page html
            response = self.graph.stream_page()
        elif request.path.endswith('/plot'):  # request for initial plot JSON
            response = self.graph.plot_json()
        elif request.path.endswith('/update_eeg'):  # request for eeg stream update
            response = self.graph.update_json(self.eeg_buffer, self.eeg_lock)  # get update from EEG buffer
        elif request.path.endswith('/update_fourier'):  # request for fourier update
            self.fourier()  # perform FFT
            response = self.graph.update_json(self.fourier_buffer, self.fourier_lock)  # get update from fourier buffer
        elif request.path.endswith('/filter_slider'):  # filter slider was moved
            vals = request.header['values'].split(',')
            self.min_freq = float(vals[0])
            self.max_freq = float(vals[1])
            response = Response(204)  # no content successful response
        else:
            self.debug("Path not recognized: {}".format(request.path), 2)
            return
        self.send(response, request.origin)

    def fourier(self):
        """ Calculates the FFT from all EEG data available """
        data = self.eeg_buffer.read_all(self.fourier_all_lock)  # dict of all current data
        fourier_dict = {name+'_fourier': [] for name in self.channels}
        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        freqs = np.fft.fftfreq(N, 1/self.sample_rate)[:N//2]  # frequency array
        fourier_dict['frequencies'] = freqs.tolist()  # numpy types are not JSON serializable
        for name, eeg_data in data.items():
            fft = (np.fft.fft(eeg_data)[:N//2])/N  # half frequency range and normalize
            fft = np.sqrt(np.real(fft)**2 + np.imag(fft)**2)
            freq_filter = np.logical_or(freqs < self.min_freq, freqs > self.max_freq)
            fft[freq_filter] = 1e-7  # log scale can't plot 0
            fourier_dict[name+'_fourier'] = fft.tolist()  # numpy types are not JSON serializable
        fourier_json = json.dumps(fourier_dict)
        self.fourier_buffer.write(fourier_json)





