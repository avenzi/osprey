import numpy as np
from scipy import signal
from time import sleep, time
import json

from lib.lib import Analyzer
from app.bokeh_layouts.eeg_stream import config as WIDGET_CONFIG


class TestAnalyzer(Analyzer):
    def __init__(self, *args):
        super().__init__(*args)

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        data = self.database.read_data(self.target_id, self.id)
        if not data:
            sleep(0.1)
            return

        # perform some operation on the data
        for key in data.keys():
            for i in range(len(data[key])):
                if key == 'time':
                    continue
                data[key][i] *= 10

        # output processed data to new stream
        self.database.write_data(self.id, data)


class EEGAnalyzer(Analyzer):
    """ Base class for the other two EEG analyzer streams"""
    def __init__(self, *args):
        super().__init__(*args)

        # Initial information
        self.sample_rate = None
        self.channels = []
        self.widgets = WIDGET_CONFIG  # all widget parameters for fourier and filtering
        self.head_x, self.head_y = [], []

    def start(self):
        """ extends streamer start method before loop """
        try:
            self.sample_rate = int(self.info['sample_rate'])
            self.channels = self.info['channels'].split(',')  # its a comma separated string

            # x/y positions for electrodes in head plots

            with open('app/static/electrodes.json', 'r') as f:
                all_names = json.loads(f.read())
            for name in self.channels:  # get coordinates of electrodes by name
                self.head_x.append(all_names[name][0])
                self.head_y.append(all_names[name][1])

        except Exception as e:
            self.throw("Failed to start {}")

        super().start()

    def json(self, dic):
        """ Gets updated widget values from a socketIO json message """
        # Content is a JSON string with a single key-value pair
        key, value = list(dic.items())[0]

        # prevent bandpass/bandstop range sliders from hitting the edges
        if key in ['pass_range', 'stop_range']:
            if value[1] >= self.sample_rate/2:
                value[1] = (self.sample_rate/2 - 0.5)
            if value[0] <= 0:
                value[0] = 0.1

        # filters needs to be updated
        if 'pass' in key:
            self.pass_update = True
        elif 'stop' in key:
            self.stop_update = True

        # store the new updated value
        self.widgets[key] = value


class EEGFilterStream(EEGAnalyzer):
    """ Analyzes the raw EEG data for filtering """

    def __init__(self, *args):
        super().__init__(*args)
        self.pass_sos = None     # current SOS. Created by create_filter_sos() in eeg_stream.py
        self.pass_sos_init = []  # list of SOS initial values
        self.pass_update = True  # Flag to set when a new SOS is requestedm
        self.stop_sos = None
        self.stop_sos_init = []
        self.stop_update = True

    def loop(self):
        """ Maine execution loop """
        data = self.database.read_data(self.target_id, self.id)
        if not data:
            sleep(0.1)
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


class EEGFourierStream(EEGAnalyzer):
    """ Analyzes the filtered data from EEGFilterStream """
    def loop(self):
        """ Maine execution loop """
        # samples needed to read for a given time window
        samples = int(self.widgets['fourier_window'] * self.sample_rate)
        filtered_data = self.database.read_data(self.target_id, self.id, count=samples)
        if not filtered_data:
            sleep(0.1)
            return

        fourier_data = self.fourier(filtered_data)  # fourier analysis
        headplot_data = self.headplot(fourier_data)  # headplot spectrogram from fourier

        self.database.write_snapshot('fourier:' + self.id, fourier_data)
        self.database.write_snapshot('headplot:' + self.id, headplot_data)

        # Slow down rate of performing fourier transforms.
        # They appear to be having a significant impact on CPU usage.
        # The process of writing the data to the database still takes longer, but
        # it looks like the FFT is the CPU intensive part, especially with high FFT time windows.
        sleep(0.5)

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

    def headplot(self, fourier_data):
        """ Calculates headplot values, then dumps it to a new stream """
        # data to send will be a dictionary of band names with amplitude data
        # The order is the same as self.channels
        headplot = {'x': self.head_x, 'y': self.head_y}

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

            # self.debug("{}: {}-{}".format(band, low, high))

            for name in self.channels:  # for each channel
                # TODO experiment with avg/median. Compute in browser?
                val = np.mean(fourier_data[name][low:high])  # band power RMS
                headplot[band].append(val)  # append value to list of channels in this band

        return headplot








