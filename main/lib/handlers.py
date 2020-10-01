from bokeh.plotting import figure
from bokeh.models import AjaxDataSource
from bokeh.layouts import layout
from scipy import signal
import numpy as np
import json

from server_lib import Handler, GraphStream
from lib import Request, Response, DataBuffer, RingBuffer

# EEG page Bokeh Layout
from pages.eeg_layout import config, configure_layout, create_sos


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
        self.buffer_lock = self.buffer.get_ticket()

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
        self.fourier_lock = None  # ticket to read from Fourier buffer

        self.spectrogram_buffer = None
        self.spectrogram_lock = None  # ticket to read from Fourier buffer
        self.spec_time = 0  # counter for how many  slices have been sent for the spectrogram

        # EEG filtering
        self.filter_sos = None     # current SOS. Created by create_sos() in eeg_layout.py
        self.filter_sos_init = []  # list of SOS initial values
        self.filter_update = True  # Flag to set when a new SOS is requested
        self.notch_ba = None
        self.notch_ba_init = []
        self.notch_update = True

        # dictionary of values for all widgets, imported from /pages/eeg_widgets
        self.page_config = config

    def INIT(self, request):
        """ Handles INIT request from client """
        self.channels = request.header['channels'].split(',')  # list of EEG channel names
        self.sample_rate = float(request.header['sample_rate'])  # data points per second

        # Massive Bokeh layout configuration imported from /pages/eeg_layout.py
        bokeh_layout = configure_layout(self.id, self.channels)

        # pass Bokeh layout object into GraphStream
        self.graph = GraphStream(bokeh_layout)

        # size of EEG buffer (# of data points to keep).
        # FFT window is in seconds, sample rate is data points per second.
        size = int(self.page_config['fourier_window'] * self.sample_rate)

        self.eeg_buffer = RingBuffer(self.channels+['time'], size)
        self.eeg_lock = self.eeg_buffer.get_ticket()

        self.fourier_buffer = DataBuffer()
        self.fourier_lock = self.fourier_buffer.get_ticket()

        self.spectrogram_buffer = DataBuffer()
        self.spectrogram_lock = self.spectrogram_buffer.get_ticket()

    def INGEST(self, request):
        """ Handle EEG data received from Pi """
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
            # reset counter so spectrogram starts at correct spot
            self.spec_time = self.page_config['spectrogram_size']
            response = self.graph.plot_json()

        elif request.path.endswith('/update_eeg'):  # request for eeg stream update
            # get update from EEG buffer
            response = self.graph.update_json(self.eeg_buffer, self.eeg_lock)

        elif request.path.endswith('/update_fourier'):  # request for fourier update
            # get update from fourier buffer
            self.fourier()  # perform FFT
            response = self.graph.update_json(self.fourier_buffer, self.fourier_lock)

        elif request.path.endswith('/update_spectrogram'):
            # get update from fourier buffer
            response = self.graph.update_json(self.spectrogram_buffer, self.spectrogram_lock)
            if response.code == 200:  # if sending new data (if no data is sent, code is 304)
                self.spec_time += 1   # increment counter
        else:
            self.debug("Path not recognized: {}".format(request.path), 2)
            return

        self.send(response, request.origin)

    def POST(self, request):
        """ Handles POST request sent. Right now used to update widgets """
        if request.path.endswith('/widgets'):  # A widget was updated
            # Content is a JSON string with a single key-value pair
            json_string = request.content.decode(self.encoding)  # decode from bytes
            key, value = list(json.loads(json_string).items())[0]

            # Converting the value from JS types in string form to python types
            if key in ['bandpass_toggle', 'notch_toggle']:  # JS bools
                if value == 'false':  # I am ashamed that I have to do this
                    value = False
                if value == 'true':
                    value = True

            elif key in ['bandpass_range']:  # range slider gives comma-separated values
                value = [float(i) for i in value]

            elif key in ['bandpass_order', 'notch_order', 'fourier_window']:  # ints
                value = int(value)

            elif key in ['notch_center']:  # floats
                value = float(value)
            # band pass/stop filter type is already a string

            # filter needs to be updated
            self.filter_update = True

            # store the new updated value in the page_config dictionary
            self.page_config[key] = value
            response = Response(204)  # no content, successful response

        else:
            self.debug("Path not recognized for POST request: {}".format(request.path), 2)
            return

        self.send(response, request.origin)

    def filter(self, data):
        """ Performs frequency filters on the input dictionary of data in-place """
        # Bandpass filters
        if self.page_config['filter_toggle']:
            if self.filter_update:  # a new filter was requested
                self.filter_sos = create_sos(self.sample_rate, self.page_config)
                init = signal.sosfilt_zi(self.filter_sos)  # get initial conditions for this sos
                self.filter_sos_init = [init] * len(self.channels)  # for each channel
                self.filter_update = False  # filter has been updated
                # TODO: When updating the filter and re-calculating the initial conditions,
                #  all channels get a huge spike that messes up the FFT and Spectrogram.
                #  I mean it goes away once time passes it's just annoying. At least you have a
                #  record of when a new filter was implemented.

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.filter_sos_init[i] = signal.sosfilt(self.filter_sos, data[name], zi=self.filter_sos_init[i])

    def denoise(self, data):
        """ Performs de-noising algorithms on the input dictionary of data in-place """
        return

    def fourier(self):
        """ Calculates the FFT from all EEG data available """
        data = self.eeg_buffer.read_all()  # dict of all current data

        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        freqs = np.fft.fftfreq(N, 1/self.sample_rate)[:N//2]  # frequency array

        spectro_slice = np.zeros(len(freqs))  # array of zeros for the spectrogram slice

        fourier_dict = {'frequencies': freqs.tolist()}  # numpy types are not JSON serializable

        for name, channel_data in data.items():
            fft = (np.fft.fft(channel_data)[:N//2])/N  # half frequency range and normalize
            fft = np.sqrt(np.real(fft)**2 + np.imag(fft)**2)

            # set fft column
            fourier_dict[name] = fft.tolist()

            # Add square of fft to spectrogram slice
            #spectro_slice += fft*fft
            if name in ['Fz', 'Cz', 'Cd', 'C1', 'C0']:
                spectro_slice += fft

        fourier_json = json.dumps(fourier_dict)
        self.fourier_buffer.write(fourier_json)

        spectro_dict = {
            #'slice': [[np.sqrt(spectro_slice/len(freqs)).tolist()]],  # normalize + Bokeh format
            'slice': [[spectro_slice.tolist()]],
            'spec_time': [self.spec_time]}  # time position of FFT slice

        spectro_json = json.dumps(spectro_dict)
        self.spectrogram_buffer.write(spectro_json)





