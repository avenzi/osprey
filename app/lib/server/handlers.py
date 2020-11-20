from bokeh.plotting import figure
from bokeh.models import AjaxDataSource, Slider, CustomJS
from bokeh.layouts import layout
from scipy import signal
import numpy as np
import json

from .server_lib import Handler, GraphStream, PAGES_PATH
from ..lib import Request, Response, DataBuffer, RingBuffer, MovingAverage

# EEG page Bokeh Layout
from .pages.eeg_layout import config, configure_layout, create_filter_sos


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


class ECGHandler(Handler):
    """ Handles ECG stream """
    def __init__(self):
        super().__init__()

        self.frames_sent = 0
        self.frames_received = 0

        self.sample_rate = 0  # sampling rate of board
        self.ecg_channels = []  # list of ECG channel name strings

        self.pulse_channels = []  # list of pulse channel name strings
        self.pulse_window = 10  # maximum window for heart rate in seconds
        self.heart_rate = MovingAverage(10)  # heart rate moving average

        # need a list of channel names, so most of these are initialized in the INIT method
        self.graph = None

        self.ecg_store_interval = 60  # interval at which to save data to a file in seconds
        self.ecg_buffer = None
        self.ecg_lock = None  # ticket to read from buffer

    def INIT(self, request):
        """ Handles INIT request from client """
        self.sample_rate = float(request.header['sample_rate'])  # data points per second
        self.ecg_channels = request.header['ecg_channels'].split(',')
        self.pulse_channels = request.header['pulse_channels'].split(',')

        # Create Bokeh figures
        source = AjaxDataSource(
            data_url='/update?id={}'.format(self.id),
            method='GET',
            polling_interval=100,  # in milliseconds
            mode='append',  # append to existing data
            max_size=int(self.sample_rate*5),  # display last 5 seconds
            if_modified=True)  # if_modified ignores responses sent with code 304 and not cached.

        ecg_list = []
        for i in range(len(self.ecg_channels)):
            fig = figure(
                title=self.ecg_channels[i],
                x_axis_label='time', y_axis_label='???',
                plot_width=600, plot_height=150,
                toolbar_location=None
            )
            fig.line(x='time', y=self.ecg_channels[i], source=source)
            ecg_list.append(fig)

        # Pulse figure
        pulse = figure(
            title='Pulse Sensor',
            x_axis_label='time', y_axis_label='Sensor Output',
            plot_width=600, plot_height=150,
            toolbar_location=None
        )
        pulse.line(x='time', y=self.pulse_channels[0], source=source)

        # Heart rate figure
        heart_rate = figure(
            title='Heart Rate',
            x_axis_label='time', y_axis_label='BPM',
            plot_width=600, plot_height=150,
            toolbar_location=None
        )
        heart_rate.circle(x='time', y='heart_rate', source=source)

        # create layout
        lay = layout([[ecg_list, [pulse, heart_rate]]])
        self.graph = GraphStream(lay)  # pass layout into GraphStream object

        size = int(self.ecg_store_interval * self.sample_rate)  # store interval in number of samples
        self.ecg_buffer = RingBuffer(self.ecg_channels+['heart_rate', 'time'], size, './data/ECG_data')
        self.ecg_lock = self.ecg_buffer.get_ticket()

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(request.encoding)  # raw JSON string
        data = json.loads(data)  # translate to dictionary
        data = self.calculate_heart_rate(data)  # adds heart rate to data
        self.ecg_buffer.write(data)  # save to buffer
        self.frames_received += 1
        self.debug("Ingested ECG data (frame {})".format(self.frames_received), 3)

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
            response = self.graph.update_json(self.ecg_buffer, self.ecg_lock)
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
            if key in ['heartbeat_threshold']:  # ints
                value = int(value)

            # store the new updated value
            self.pulse_threshold = value
            response = Response(204)  # no content, successful response

        else:
            self.debug("Path not recognized for POST request: {}".format(request.path), 2)
            return

        self.send(response, request.origin)

    def calculate_heart_rate(self, new_data):
        """
        Calculates heart rate within the last pulse window
        Adds heart rate to the data dictionary and returns it
        <new_data> new data to add heart rate to.
        """
        samples = int(self.pulse_window * self.sample_rate)
        all_pulse_data = self.ecg_buffer.read_length(samples)[self.pulse_channels[0]]
        new_pulse_data = new_data[self.pulse_channels[0]]  # new pulse data to be added
        pulse_data = all_pulse_data + new_pulse_data  # all available pulse data

        window = min(int(self.pulse_window*self.sample_rate), len(pulse_data)-1)  # size of time window
        pulses = pulse_data[-window:]  # pulse data in time window

        # get pulse peaks above pulse_threshold, and a minimum distance of a 10th of the sample rate apart.
        # distance is used to regulate the space between peaks - right now this is to account for the plateaus
        peaks, _ = signal.find_peaks(pulses, distance=self.sample_rate/4, prominence=400)
        bpm = (len(peaks)/window)*self.sample_rate*60  # beats per minute in this window
        heart_rate = self.heart_rate.add(bpm)  # add value to moving average and get result

        #self.debug("Window: {}, peaks: {}".format(window, len(peaks)))

        # add the calculated heart rate to the new data, and return it.
        # need to pad with 'nan' so the DataSource has columns of equal length.
        # Bokeh doesn't plot 'nan' points.
        new_data['heart_rate'] = ['nan']*(len(new_pulse_data)-1) + [heart_rate]
        return new_data


class EEGHandler(Handler):
    """ Handles EEG stream """
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

        self.fourier_store_interval = 0  # interval at which to save data in seconds
        self.fourier_buffer = None
        self.fourier_lock = None  # ticket to read from Fourier buffer
        self.head_plot_lock = None  # ticket for the head plots

        self.spectrogram_buffer = None
        self.spectrogram_lock = None  # ticket to read from Fourier buffer
        self.spec_time = 0  # counter for how many  slices have been sent for the spectrogram

        self.head_x, self.head_y = [], []  # x/y positions for electrodes in head plots

        # EEG filtering
        self.pass_sos = None     # current SOS. Created by create_sos() in eeg_layout.py
        self.pass_sos_init = []  # list of SOS initial values
        self.pass_update = True  # Flag to set when a new SOS is requested
        self.stop_sos = None
        self.stop_sos_init = []
        self.stop_update = True

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
        self.head_plot_lock = self.fourier_buffer.get_ticket()

        with open(PAGES_PATH+'/electrodes.json', 'r') as f:
            all_names = json.loads(f.read())
        for name in self.channels:  # get coordinates of electrodes by name
            self.head_x.append(all_names[name][0])
            self.head_y.append(all_names[name][1])

        self.spectrogram_buffer = DataBuffer()
        self.spectrogram_lock = self.spectrogram_buffer.get_ticket()

    def INGEST(self, request):
        """ Handle EEG data received from Pi """
        data = request.content.decode(request.encoding)  # raw JSON data
        data = json.loads(data)  # load into a dictionary
        self.filter(data)
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

        elif request.path.endswith('/update_headplot'):
            response = self.update_headplot()

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
            if key in ['pass_toggle', 'stop_toggle']:  # JS bools
                if value == 'false':  # I am ashamed that I have to do this
                    value = False
                if value == 'true':
                    value = True

            elif key in ['pass_range', 'stop_range']:  # range slider gives comma-separated values
                value = [float(i) for i in value]
                if value[1] >= self.sample_rate/2:
                    value[1] = (self.sample_rate/2 - 0.5)
                if value[0] <= 0:
                    value[0] = 0.1

            elif key in ['pass_order', 'stop_order', 'fourier_window']:  # ints
                value = int(value)
            # filter style is already a string

            # filters needs to be updated
            if 'pass' in key:
                self.pass_update = True
            if 'stop' in key:
                self.stop_update = True

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
        if self.page_config['pass_toggle']:
            if self.pass_update:  # a new filter was requested
                self.pass_sos = create_filter_sos('pass', self.sample_rate, self.page_config)
                init = signal.sosfilt_zi(self.pass_sos)  # get initial conditions for this sos
                self.pass_sos_init = [init] * len(self.channels)  # for each channel
                self.pass_update = False  # filter has been updated

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.pass_sos_init[i] = signal.sosfilt(self.pass_sos, data[name], zi=self.pass_sos_init[i])

        # notch filter
        # TODO: Use small bandpass filter instead?
        if self.page_config['stop_toggle']:
            if self.stop_update:  # a new filter was requested
                self.stop_sos = create_filter_sos('stop', self.sample_rate, self.page_config)
                init = signal.sosfilt_zi(self.stop_sos)  # get initial conditions for this (b, a)
                self.stop_sos_init = [init] * len(self.channels)  # for each channel
                self.stop_update = False  # filter has been updated

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.stop_sos_init[i] = signal.sosfilt(self.stop_sos, data[name], zi=self.stop_sos_init[i])

        # TODO: When updating the filter and re-calculating the initial conditions,
        #  all channels get a huge ripple that messes up the FFT and Spectrogram.
        #  It goes away once time passes, but it's annoying. At least you have a
        #  record of when a new filter was implemented.

    def fourier(self):
        """ Calculates the FFT from all EEG data available """
        samples = int(self.page_config['fourier_window'] * self.sample_rate)
        data = self.eeg_buffer.read_length(samples)  # dict of data in the fourier window

        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        if N == 0:  # no data
            self.debug("No data to compute FFT")
            return

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
            if name in ['Fp1', 'Fp2']:
                spectro_slice += fft

        fourier_json = json.dumps(fourier_dict)
        self.fourier_buffer.write(fourier_json)

        spectro_dict = {
            #'slice': [[np.sqrt(spectro_slice/len(freqs)).tolist()]],  # normalize + Bokeh format
            'slice': [[spectro_slice.tolist()]],
            'spec_time': [self.spec_time]}  # time position of FFT slice

        spectro_json = json.dumps(spectro_dict)
        self.spectrogram_buffer.write(spectro_json)

    def update_headplot(self):
        """ Calculate head plot data values and return a response object to send """
        response = Request()
        response.add_header('content-type', 'application/json')
        response.add_header('Cache-Control', 'no-store')

        # data to send will be a dictionary of band names with amplitude data
        # The order is the same as self.channels
        headplot = {}

        # read most recent data from the buffer
        data = self.fourier_buffer.read(self.head_plot_lock, block=False)
        if data is None:  # no new data is available yet
            response.add_response(304)  # not modified
            return response
        data = json.loads(data)  # convert to dict

        for band in self.page_config['bands'].keys():  # for each band type
            headplot[band] = []
            low, high = self.page_config['bands'][band]  # get frequency range for this band

            # multiply by window size to get the frequency index because the FFT is stretched
            low = int(low*self.page_config['fourier_window'])
            high = int(high*self.page_config['fourier_window'])+1

            # if the fourier data doesn't go as high as the high value wants.
            # This would happen if the sampling rate is too low to measure this frequency.
            if high > len(data[self.channels[0]]):
                high = len(data[self.channels[0]])

            #self.debug("{}: {}-{}".format(band, low, high))

            for name in self.channels:  # for each channel
                # TODO experiment with avg/median. Compute in browser?
                val = np.mean(data[name][low:high])  # band power RMS
                headplot[band].append(val)  # append value to list of channels in this band

        headplot['x'] = self.head_x
        headplot['y'] = self.head_y
        response.add_response(200)
        response.add_content(json.dumps(headplot))
        return response





