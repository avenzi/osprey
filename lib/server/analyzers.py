import numpy as np
from scipy import signal
from time import sleep, time
import json

from lib.lib import Analyzer
from lib.server.analysis_lib import MovingAverage
from lib.database import DatabaseError
from app.bokeh_layouts.eeg_stream import default_filter_widgets as EEG_FILTER_WIDGETS
from app.bokeh_layouts.eeg_stream import default_fourier_widgets as EEG_FOURIER_WIDGETS
from app.bokeh_layouts.ecg_stream import default_filter_widgets as ECG_FILTER_WIDGETS
from app.bokeh_layouts.ecg_stream import default_fourier_widgets as ECG_FOURIER_WIDGETS


class TestAnalyzer(Analyzer):
    def start(self):
        # Get IDs for each data stream
        self.random_11 = self.targets['Test Group 1']['Random 1']['id']
        self.random_12 = self.targets['Test Group 1']['Random 2']['id']
        self.random_21 = self.targets['Test Group 2']['Random 1']['id']
        self.random_22 = self.targets['Test Group 2']['Random 2']['id']

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        all_data = {
            '11': self.database.read_data(self.random_11),
            '12': self.database.read_data(self.random_12),
            '21': self.database.read_data(self.random_21),
            '22': self.database.read_data(self.random_22)
        }

        if not any(all_data.values()):  # got no data from any stream
            sleep(0.5)
            return

        # perform some operation on the data.
        # This averages the value of the 3 columns for each stream
        # need separate time columns so bokeh knows how much to plot for each since they are separate streams
        for name, data in all_data.items():
            if not data:  # no data gotten for this one
                continue
            a = np.array(data['val_1'])
            b = np.array(data['val_2'])
            c = np.array(data['val_3'])
            output = {
                'data': np.average((a, b, c), axis=0),
                'time': data['time']}

            self.database.write_data(name+':'+self.id, output)

        sleep(0.5)


class FunctionAnalyzer(Analyzer):
    """ Analyzer for running data through arbitrary python functions stored in local/pipelines/ """
    def __init__(self, *args):
        super().__init__(*args)
        self.target_id = None  # stream ID of the target data stream

        # List of python functions for data to be run through before written back to the database
        self.functions = []

    def start(self):
        """ streamer start method before loop is executed """
        try:  # grab the ID of the target stream
            self.target_id = self.targets[self.group]['Filtered']['id']
        except:
            raise Exception("Missing info.".format(self))

    def loop(self):
        """ Maine execution loop """
        data = self.database.read_data(self.target_id)
        if not data:  # if no data read, wait half a sec to loop again
            sleep(0.5)
            return

        for function in self.functions:  # for each pipeline function
            data = function(data)

        # after data has been put through all transforms, write it back to the database
        self.database.write_data(self.id, data)

    def json(self, lst):
        """ Gets list of updated file names from which to retrieve pipeline functions from """
        print("GOT PIPELINE: ", lst)
        transform = None  # make the editor happy because "transform" technically isn't defined
        self.functions = []
        for filename in lst:  # for each file in the received list of file names
            exec("from {} import transform".format(filename))  # import a function named transform from this file
            # todo: just check to make sure there is one method defined in the file, then use that one regardless of
            #  what is is technically defined as. Avoids the requirement of a specific name.
            self.functions.append(transform)  # associate that function with this file name
        self.database.set_info(self.id, json.dumps(self.functions))  # save in database


########################
# EEG and ECG Raw Data Analyzers


class SignalAnalyzer(Analyzer):
    """ Base class for the other two EEG analyzer streams"""
    def __init__(self, *args):
        super().__init__(*args)

        # Initial information
        self.sample_rate = None
        self.channels = []
        self.widgets = {}

    def start(self):
        """ streamer start method before loop is executed """
        try:
            self.get_info()
        except:
            raise Exception("Missing info.".format(self))

    def get_info(self):
        pass


class SignalFilter(SignalAnalyzer):
    """ Base class for filtering time series biosignal data """
    def __init__(self, *args):
        super().__init__(*args)
        self.pass_sos = None     # current SOS. Created by create_filter_sos() in eeg_stream.py
        self.pass_sos_init = []  # list of SOS initial values
        self.pass_update = True  # Flag to set when a new SOS is requestedm
        self.stop_sos = None
        self.stop_sos_init = []
        self.stop_update = True

        self.raw_id = None

    def loop(self):
        """ Maine execution loop """
        data = self.database.read_data(self.raw_id)
        if not data:
            sleep(0.5)
            return
        filtered_data = self.filter(data)  # perform filtering
        self.database.write_data(self.id, filtered_data)

    def filter(self, data):
        """ Performs frequency filters on the input dictionary of data """
        # Bandpass filters
        if self.widgets['pass_toggle']:
            if self.pass_update:  # a new filter was requested
                self.pass_sos = self.create_filter_sos('pass')
                init = signal.sosfilt_zi(self.pass_sos)  # get initial conditions for this sos
                self.pass_sos_init = [init] * len(self.channels)  # for each channel
                self.pass_update = False  # filter has been updated

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.pass_sos_init[i] = signal.sosfilt(self.pass_sos, data[name], zi=self.pass_sos_init[i])

        # notch filter
        if self.widgets['stop_toggle']:
            if self.stop_update:  # a new filter was requested
                self.stop_sos = self.create_filter_sos('stop')
                init = signal.sosfilt_zi(self.stop_sos)  # get initial conditions for this (b, a)
                self.stop_sos_init = [init] * len(self.channels)  # for each channel
                self.stop_update = False  # filter has been updated

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.stop_sos_init[i] = signal.sosfilt(self.stop_sos, data[name], zi=self.stop_sos_init[i])

        # TODO: When updating the filter and re-calculating the initial conditions,
        #  all channels get a huge ripple that messes up the FFT and Spectrogram.
        #  It goes away once time passes, but it's annoying. Don't think there
        #  is a way around this, though.
        return data

    def create_filter_sos(self, name):
        """
        Returns the Second Order Sections of the given filter design.
        [name] prefix used to get config attributes

        [self.widgets] dict: Configuration dictionary seen in bokeh_layouts/eeg_stream.py
            [name_type] string: bandpass, bandstop, lowpass, highpass
            [name_style] string: Bessel, Butterworth, Chebyshev 1, Chebyshev 2, Elliptic
            [name_crit] tuple: (low, high) critical values for the filter cutoffs
            [name_order] int: Order of filter polynomial
            [name_ripple] tuple: (max gain, max attenuation) for chebyshev and elliptic filters
        """
        type = self.widgets[name + '_type']
        style = self.widgets[name + '_style']
        range = self.widgets[name + '_range']
        order = self.widgets[name + '_order']
        ripple = self.widgets[name + '_ripple']

        if style == 'Bessel':
            sos = signal.bessel(order, range, fs=self.sample_rate, btype=type, output='sos')
        elif style == 'Butterworth':
            sos = signal.butter(order, range, fs=self.sample_rate, btype=type, output='sos')
        elif style == 'Chebyshev 1':
            sos = signal.cheby1(order, ripple[0], range, fs=self.sample_rate, btype=type, output='sos')
        elif style == 'Chebyshev 2':
            sos = signal.cheby2(order, ripple[1], range, fs=self.sample_rate, btype=type, output='sos')
        elif style == 'Elliptic':
            sos = signal.ellip(order, ripple[0], ripple[1], range, fs=self.sample_rate, btype=type, output='sos')
        else:
            return None
        return sos

    def json(self, dic):
        """ Gets updated widget values from a socketIO json message """
        for key in dic.keys():
            val = dic[key]
            # prevent bandpass/bandstop range sliders from hitting the edges
            if key in ['pass_range', 'stop_range']:
                if val[1] >= self.sample_rate/2:
                    val[1] = (self.sample_rate/2 - 0.5)
                if val[0] <= 0:
                    val[0] = 0.1

            # filters needs to be updated
            if 'pass' in key:
                self.pass_update = True
            elif 'stop' in key:
                self.stop_update = True

            # store the new updated value
            self.widgets[key] = val

        # write widgets as JSON string to database under the key 'widgets'
        self.database.set_info(self.id, {'widgets': json.dumps(self.widgets)})


class SignalFourier(SignalAnalyzer):
    """ Base class for performing FFTs on a set of signals """

    def __init__(self, *args):
        super().__init__(*args)
        self.pass_sos = None  # current SOS. Created by create_filter_sos() in eeg_stream.py
        self.pass_sos_init = []  # list of SOS initial values
        self.pass_update = True  # Flag to set when a new SOS is requestedm
        self.stop_sos = None
        self.stop_sos_init = []
        self.stop_update = True

        # Make sure that the derived SignalFilter targets streams in its own group with the names 'Raw' and 'Filtered'
        self.raw_id = None
        self.filtered_id = None

    def loop(self):
        """ Maine execution loop """
        # samples needed to read for a given time window
        samples = int(self.widgets['fourier_window'] * self.sample_rate)
        filtered_data = self.database.read_data(self.filtered_id, count=samples)
        if not filtered_data:
            sleep(0.1)
            return

        fourier_data = self.fourier(filtered_data)  # fourier analysis
        fourier_data['time'] = filtered_data['time'][0]  # use latest time stamp from filtered data
        self.database.write_snapshot(self.id, fourier_data)

        # Slow down rate of performing fourier transforms.
        # They appear to be having a significant impact on CPU usage.
        # The process of writing the data to the database still takes longer, but
        # it looks like the FFT is the CPU intensive part, especially with high FFT time windows.
        sleep(1)

    def fourier(self, data):
        """ Calculates the FFT of a slice of data """
        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        freqs = np.fft.fftfreq(N, 1 / self.sample_rate)[:N // 2]  # frequency array

        # numpy types are not JSON serializable, so they must be converted to a list
        fourier_dict = {'frequencies': freqs.tolist()}
        # spectro_dict = {'spec_time': [self.spec_time]}

        for name, channel_data in data.items():
            if name == 'time':
                continue  # don't perform an FFT on the time series lol

            fft = (np.fft.fft(channel_data)[:N // 2]) / N  # half frequency range and normalize
            fft = np.sqrt(np.real(fft) ** 2 + np.imag(fft) ** 2)

            # set fft column
            fourier_dict[name] = fft.tolist()

            # Add square of fft to spectrogram slice
            # must be 2D list because this is being put into an image glyph
            # spectro_dict[name] = [[fft.tolist()]]

        return fourier_dict

        # spectrogram
        # self.spectrogram_buffer.write(spectro_dict)

    def json(self, dic):
        """ Gets updated widget values from a socketIO json message """
        for key in dic.keys():
            self.widgets[key] = dic[key]

        # write widgets as JSON string to database under the key 'widgets'
        self.database.set_info(self.id, {'widgets': json.dumps(self.widgets)})


class EEGFilter(SignalFilter):
    """ Analyzes the raw EEG data for filtering """

    def __init__(self, *args):
        super().__init__(*args)
        self.widgets = EEG_FILTER_WIDGETS  # all widget parameters for fourier and filtering

    def get_info(self):
        # Make sure that the derived SignalFilter targets streams in its own group with the name 'Raw'.
        # Get info from database
        raw = self.targets[self.group]['Raw']
        self.raw_id = raw['id']
        self.sample_rate = raw['sample_rate']
        self.channels = raw['channels'].split(',')  # its a comma separated string


class ECGFilter(SignalFilter):
    """ Analyzes the raw ECG data for filtering """

    def __init__(self, *args):
        super().__init__(*args)
        self.widgets = ECG_FILTER_WIDGETS  # all widget parameters for fourier and filtering

    def get_info(self):
        # Make sure that the derived SignalFilter targets streams in its own group with the name 'Raw'.
        # Get info from raw database
        raw = self.targets[self.group]['Raw']
        self.raw_id = raw['id']
        self.sample_rate = raw['sample_rate']
        self.channels = raw['ecg_channels'].split(',')  # its a comma separated string


class EEGFourier(SignalFourier):
    """ Analyzes the filtered data from EEGFilterStream """
    def __init__(self, *args):
        super().__init__(*args)
        self.widgets = EEG_FOURIER_WIDGETS  # all widget parameters for fourier and filtering
        self.head_x, self.head_y, self.head_names = [], [], []

    def get_info(self):
        raw = self.targets[self.group]['Raw']
        filtered = self.targets[self.group]['Filtered']
        self.raw_id = raw['id']
        self.filtered_id = filtered['id']
        self.sample_rate = raw['sample_rate']
        self.channels = raw['channels'].split(',')  # its a comma separated string

        # x/y positions for electrodes in head plots
        with open('app/static/electrodes.json', 'r') as f:
            all_names = json.loads(f.read())
        self.head_x, self.head_y, self.head_names = [], [], []  # needs to be reset incase the stream is stopped and started again
        for name in self.channels:  # get coordinates of electrodes by name
            self.head_names.append(name)
            self.head_x.append(all_names[name][0])
            self.head_y.append(all_names[name][1])

    def loop(self):
        """ Maine execution loop (Overriding SignalFourier) """
        # samples needed to read for a given time window
        samples = int(self.widgets['fourier_window'] * self.sample_rate)
        filtered_data = self.database.read_data(self.filtered_id, count=samples)
        if not filtered_data:
            sleep(0.5)
            return

        fourier_data = self.fourier(filtered_data)  # fourier analysis
        fourier_data['time'] = filtered_data['time'][-1]  # use latest time stamp from filtered data.

        headplot_data = self.headplot(fourier_data)  # headplot spectrogram from fourier
        headplot_data['time'] = filtered_data['time'][-1]  # use latest time stamp from filtered data

        self.database.write_snapshot('fourier:' + self.id, fourier_data)
        self.database.write_snapshot('headplot:' + self.id, headplot_data)

        # Slow down rate of performing fourier transforms.
        # They appear to be having a significant impact on CPU usage.
        # The process of writing the data to the database still takes longer, but
        # it looks like the FFT is the CPU intensive part, especially with high FFT time windows.
        sleep(1)

    def headplot(self, fourier_data):
        """ Calculates headplot values, then dumps it to a new stream """
        # data to send will be a dictionary of band names with amplitude data
        # The order is the same as self.channels
        headplot = {'x': self.head_x, 'y': self.head_y, 'channel': self.head_names}

        for band in self.widgets['bands'].keys():  # for each band type
            headplot[band] = []
            low, high = self.widgets['bands'][band]  # get frequency range for this band

            # multiply by window size to get the frequency index because the FFT is stretched
            low = int(low * self.widgets['fourier_window'])
            high = int(high * self.widgets['fourier_window']) + 1

            # if the fourier data doesn't go as high as the high value wants.
            # This would happen if the sampling rate is too low to measure this frequency.
            if high > len(fourier_data[self.channels[0]]):
                high = len(fourier_data[self.channels[0]])

            for name in self.channels:  # for each channel
                # TODO experiment with avg/median. Compute in browser?
                val = np.mean(fourier_data[name][low:high])  # band power RMS
                headplot[band].append(val)  # append value to list of channels in this band

        return headplot


class ECGFourier(SignalFourier):
    """ Analyzes the filtered data from ECGFilter """
    def __init__(self, *args):
        super().__init__(*args)
        self.widgets = ECG_FOURIER_WIDGETS  # all widget parameters for fourier and filtering

    def get_info(self):
        raw = self.targets[self.group]['Raw']
        filtered = self.targets[self.group]['Filtered']
        self.raw_id = raw['id']
        self.filtered_id = filtered['id']
        self.sample_rate = raw['sample_rate']
        self.channels = raw['ecg_channels'].split(',')  # its a comma separated string


class PulseAnalyzer(Analyzer):
    """ Analyzes a signal for a heart beat """
    def __init__(self, *args):
        super().__init__(*args)

        # Initial information
        self.raw_id = None
        self.sample_rate = None
        self.channels = []
        self.window = 10  # time window in which to calculate
        self.heart_rate = MovingAverage(self.window)  # heart rate moving average

    def get_info(self):
        raw = self.targets[self.group]['Raw']
        self.raw_id = raw['id']
        self.sample_rate = raw['sample_rate']
        self.channels = raw['channels'].split(',')  # its a comma separated string

    def loop(self):
        """ Maine execution loop """
        samples = int(self.window*self.sample_rate)
        raw = self.database.read_data(self.raw_id, count=samples)
        if not raw:
            sleep(0.5)
            return

        pulse_data = raw[self.channels[0]]
        heart_rate = self.calc_heart_rate(pulse_data)  # perform filtering
        output = {'heart_rate': heart_rate, 'time': raw['time'][-1]}
        self.database.write_data(self.id, output)
        sleep(0.5)

    def calc_heart_rate(self, data):
        """ Calculates heart rate """
        window = 10  # 10 second time window
        samples = int(window*self.sample_rate)  # window of 10 seconds

        window = min(samples, len(data)-1)  # if current data is less than time window
        pulses = data[-window:]  # pulse data in time window

        # get pulse peaks above pulse_threshold, and a minimum distance of a 10th of the sample rate apart.
        # distance is used to regulate the space between peaks - right now this is to account for the plateaus
        peaks, _ = signal.find_peaks(pulses, distance=self.sample_rate/4, prominence=400)
        bpm = (len(peaks)/window)*self.sample_rate*60  # beats per minute in this window
        heart_rate = self.heart_rate.add(bpm)  # add value to moving average and get result

        #self.debug("Window: {}, peaks: {}".format(window, len(peaks)))
        return heart_rate










