import numpy as np
from scipy import signal
from time import sleep
import json

from lib.lib import Streamer, Namespace
from app.bokeh_layouts.eeg_stream import config, create_filter_sos

"""
Analyzer streams in Redis are indexed like so:
stream:string_identifier:target_stream_id
Note that it is identified by the original stream's ID, not by it's own.
The info hash is identified the same way:
info:analyzer_prefix:target_stream_id
"""


class TestAnalyzer(Streamer):
    target_name = 'TestStreamer'  # name of streamer type to analyze

    def __init__(self, *args):
        super().__init__(*args)
        self.type = 'plot'
        self.show = 'false'
        self.target_id = None

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        data = self.database.read_data(self.id, self.target_id)
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
        self.database.write_data('multiplied:'+self.target_id, data)


class EEGAnalyzer(Streamer):
    target_name = 'EEGStreamer'  # name of streamer type to analyze

    def __init__(self, *args):
        super().__init__(*args)
        self.type = 'plot'
        self.show = 'false'
        self.target_id = None

        # Initial information
        self.sample_rate = None
        self.channels = []
        self.widgets = config  # all widget parameters for fourier and filtering
        
        # EEG filtering
        self.pass_sos = None     # current SOS. Created by create_filter_sos() in eeg_stream.py
        self.pass_sos_init = []  # list of SOS initial values
        self.pass_update = True  # Flag to set when a new SOS is requestedm
        self.stop_sos = None
        self.stop_sos_init = []
        self.stop_update = True

        # headplot values
        self.head_x, self.head_y = [], []  # x/y positions for electrodes in head plots

    def start(self):
        """ extends streamer start method before loop """
        info = self.database.read_info(self.target_id)  # get info dict
        self.sample_rate = int(info['sample_rate'])
        self.channels = info['channels'].split(',')

        # register namespace to receive widget updates (namespace is own ID)
        class AnalyzerNamespace(Namespace):
            def on_options(self, option_json):
                print("ANALYZER RECEIVED: ", option_json)
        self.register_namespace(AnalyzerNamespace, '/'+self.id)

        with open('app/static/electrodes.json', 'r') as f:
            all_names = json.loads(f.read())
        for name in self.channels:  # get coordinates of electrodes by name
            self.head_x.append(all_names[name][0])
            self.head_y.append(all_names[name][1])

        super().start()

    def loop(self):
        """ Maine execution loop """
        # samples needed to read for a given time window
        samples = int(self.widgets['fourier_window'] * self.sample_rate)
        data = self.database.read_data(self.id, self.target_id, count=samples)
        if not data:
            return

        # perform analysis
        filtered_data = self.filter(data)
        fourier_data = self.fourier(filtered_data)
        headplot_data = self.headplot(fourier_data)

        self.database.write_snapshot('fourier:'+self.target_id, fourier_data)
        self.database.write_snapshot('headplot:'+self.target_id, headplot_data)

    def filter(self, data):
        """ Performs frequency filters on the input dictionary of data """
        # Bandpass filters
        if self.widgets['pass_toggle']:
            if self.pass_update:  # a new filter was requested
                self.pass_sos = create_filter_sos('pass', self.sample_rate, self.widgets)
                init = signal.sosfilt_zi(self.pass_sos)  # get initial conditions for this sos
                self.pass_sos_init = [init] * len(self.channels)  # for each channel
                self.pass_update = False  # filter has been updated

            for i, name in enumerate(self.channels):  # for all EEG data channels
                # apply filter with initial conditions, and set new initial conditions
                data[name], self.pass_sos_init[i] = signal.sosfilt(self.pass_sos, data[name], zi=self.pass_sos_init[i])

        # notch filter
        # TODO: Use small bandpass filter instead?
        if self.widgets['stop_toggle']:
            if self.stop_update:  # a new filter was requested
                self.stop_sos = create_filter_sos('stop', self.sample_rate, self.widgets)
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

    def fourier(self, data):
        """ Calculates the FFT of a slice of data """
        N = len(list(data.values())[0])  # length of each channel in eeg data (should all be the same)
        freqs = np.fft.fftfreq(N, 1/self.sample_rate)[:N//2]  # frequency array

        # numpy types are not JSON serializable, so they must be converted to a list
        fourier_dict = {'frequencies': freqs.tolist()}
        #spectro_dict = {'spec_time': [self.spec_time]}

        for name, channel_data in data.items():
            if name == 'time':
                continue  # don't perform an FFT on the time series lol

            fft = (np.fft.fft(channel_data)[:N//2])/N  # half frequency range and normalize
            fft = np.sqrt(np.real(fft)**2 + np.imag(fft)**2)

            # set fft column
            fourier_dict[name] = fft.tolist()

            #Add square of fft to spectrogram slice
            #must be 2D list because this is being put into an image glyph
            #spectro_dict[name] = [[fft.tolist()]]

        return fourier_dict

        #spectrogram
        #self.spectrogram_buffer.write(spectro_dict)
        
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

    def json(self, json_string):
        """ Gets updated widget values from a socket """
        super().json(json_string)
        return
        # Content is a JSON string with a single key-value pair
        key, value = list(json.loads(json_string).items())[0]
        print("WIDGETS: ", key, value)

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
        self.widgets[key] = value






