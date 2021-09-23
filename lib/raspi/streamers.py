from lib.lib import Base, Streamer
from lib.raspi.pi_lib import configure_port, BytesOutput, BytesOutput2

from random import random
from time import time, sleep
from os import environ
import numpy as np


class TestStreamer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        self.frames = 10           # how many frames are in each request

        self.val_1 = 0
        self.val_2 = 1
        self.val_3 = 2

    def loop(self):
        """ Maine execution loop """
        data = {'time': [], 'val_1': [], 'val_2': [], 'val_3': []}
        for i in range(self.frames):
            self.val_1 += random()-0.5
            self.val_2 += random()-0.5
            self.val_3 += random()-0.5
            data['time'].append(time()*1000)  # seconds to milliseconds
            data['val_1'].append(self.val_1)
            data['val_2'].append(self.val_2)
            data['val_3'].append(self.val_3)
            sleep(0.05)

        self.database.write_data(self.id, data)

    def start(self):
        self.val_1 = 0
        self.val_2 = 1
        self.val_3 = 2


class SenseStreamer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        try:
            from sense_hat import SenseHat
            self.sense = SenseHat()  # sense hat object
        except Exception as e:
            print("Failed to create Sense Hat Streamer: {}".format(e))

        self.color_map = {'left': 'blue', 'right': 'green', 'up': 'red', 'down': 'yellow', 'middle': 'black'}
        self.button = 0

    def loop(self):
        """ Maine execution loop """
        data = {'time': [], 'humidity': [], 'pressure': [], 'temperature': [], 'pitch': [], 'roll': [], 'yaw': []}
        for i in range(5):
            roll, pitch, yaw = self.sense.get_orientation_degrees().values()
            data['humidity'].append(self.sense.get_humidity())
            data['pressure'].append(self.sense.get_pressure())
            data['temperature'].append((self.sense.get_temperature_from_humidity() + self.sense.get_temperature_from_pressure()) / 2)
            data['roll'].append(roll)
            data['pitch'].append(pitch)
            data['yaw'].append(yaw)
            data['time'].append(time()*1000)
            sleep(0.1)

        self.database.write_data(self.id, data)

        # get joystick data
        data = {'time': [], 'button': [], 'color': []}
        for event in self.sense.stick.get_events():
            if event.action == 'pressed':
                data['time'].append(event.timestamp*1000)
                data['button'].append(event.direction)
                data['color'].append(self.color_map[event.direction])

        self.database.write_data('button:'+self.id, data)
        sleep(0.1)

    def start(self):
        """ Extended from base class in pi_lib.py """
        # enable compass, gyro, and accelerometer to calculate orientation
        self.sense.set_imu_config(True, True, True)
        self.sense.stick.get_events()  # first call to get_events() to start recording


class LogStreamer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        self.handler = 'LogHandler'

        with open(CONFIG_PATH) as config_file:
            config = json.load(config_file)
        self.log_path = config.get('LOG_PATH') + '/log.log'
        self.client_name = config.get('NAME')

    def loop(self):
        """ Main execution loop """
        sleep(10)  # send every 10 seconds
        self.send_log()

    def START(self, request):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        # send initial information
        init_req = HTTPRequest()  # new request
        init_req.add_request('INIT')  # call INIT method on server handler
        init_req.add_header('client', self.client_name)
        self.send(init_req, request.origin)  # send init request back
        self.send_log()  # send first log immediately

        super().START(request)  # start main loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # stop main loop
        self.send_log()  # send remainder of log

    def send_log(self):
        """ Send the contents of the local log file to the requesting socket """
        resp = HTTPRequest()  # new INGEST request
        resp.add_request("INGEST")
        with Base.log_lock:  # get read lock on log file
            with open(self.log_path, 'r+') as file:
                log = file.read()  # get logs
                file.truncate(0)  # erase
        log = log.encode(self.encoding)
        resp.add_content(log)
        self.send(resp)


class VideoStreamer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        self.start_time = 0           # time of START

        self.picam_buffer = BytesOutput()  # buffer to hold images from the Picam

    def loop(self):
        """
        Main execution loop
        """
        if not self.camera.frame.complete or self.camera.frame.frame_type == self.sps:
            return
        images = self.picam_buffer.read()  # get most recent frames

        data = {
            'time': time()*1000,
            'frame': images
        }

        self.database.write_data(self.id, data)

    def start(self):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        # for some reason if the PiCamera object is defined on a different thread, start_recording will hang.
        from picamera import PiCamera, PiVideoFrameType
        self.camera = PiCamera(resolution='400x400', framerate=20)
        self.camera.rotation = 180
        self.sps = PiVideoFrameType.sps_header

        # info to send to database
        self.info['framerate'] = self.camera.framerate[0]
        self.info['width'] = self.camera.resolution.width
        self.info['height'] = self.camera.resolution.height

        # start recording
        self.camera.start_recording(self.picam_buffer,
            format='h264', quality=25, profile='constrained', level='4.2',
            intra_period=self.info['framerate'], intra_refresh='both', inline_headers=True, sps_timing=True
        )
        sleep(2)  # let camera warm up for a sec. Does weird stuff otherwise.

    def stop(self):
        """
        HTTPRequest method STOP
        Extended from the base class in pi_lib.py
        """
        try:
            self.camera.stop_recording()
            self.camera.close()  # close camera resources
        except:
            pass


class AudioStreamer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)

        try:
            # unset the DISPLAY environment variable so that PortAudio doesn't try to
            #  create an X11 connection when run from an SSH session
            del environ['DISPLAY']
        except:
            pass

        self.sample_rate = 44100
        self.stream = None  # SoundDevice Stream object created in start() and closed in stop()
        self.last_block_time = None  # timestamp of last recorded audio block

    def loop(self):
        sleep(1)

    def start(self):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """

        import sounddevice as sd

        def callback(indata, num_frames, block_time, status):
            """ Callback function for the sd.stream object """
            # indata is an array of arrays, where the second level arrays have indexes for each channel.
            # To feed this into the database, we must get rid of those second level arrays. (theres only one channel)
            outdata = []
            for channels in indata:
                outdata.append(channels[0])

            if not self.last_block_time:
                self.last_block_time = time()
                return

            # assign timestamps to all frames since last frame block time
            t = np.linspace(self.last_block_time*1000, time()*1000, num_frames)
            self.last_block_time = time()

            # recording latency
            #print('latency', self.stream.latency)

            # for some reason these metrics are broken
            #print(block_time.inputBufferAdcTime, block_time.outputBufferDacTime, block_time.currentTime)

            data = {
                'time': t,
                'data': outdata,
            }
            if status.input_overflow or status.input_underflow:
                print('overflow:', status.input_overflow, 'underflow:', status.input_underflow)
            self.database.write_data(self.id, data)

        # SoundDevice stream
        self.stream = sd.InputStream(channels=1, callback=callback, samplerate=self.sample_rate, blocksize=1000)
        self.stream.start()
        self.start_time = time()

        # info to send to database
        self.info['sample_rate'] = self.sample_rate

    def stop(self):
        """
        HTTPRequest method STOP
        Extended from the base class in pi_lib.py
        """
        try:
            self.stream.stop()
            self.stream.close()
        except:
            pass


class SynthEEGStreamer(Streamer):
    """
    Synthetic EEG streamer class for testing
    """
    def __init__(self, *args):
        super().__init__(*args)
        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        self.board_id = BoardIds.SYNTHETIC_BOARD.value  # synthetic board (-1)

        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)  # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)  # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency

        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger
        params = BrainFlowInputParams()
        self.board = BoardShim(self.board_id, params)  # board object

        # add info to send to database
        self.info['sample_rate'] = self.freq
        self.info['channels'] = ','.join(self.eeg_channel_names)

    def loop(self):
        """ Main execution loop """
        sleep(0.25)  # wait a bit for the board to collect another chunk of data
        data = {}
        for channel in self.eeg_channel_names:  # lists of channel data
            data[channel] = []

        # attempt to read from board
        # data collected in uV
        try:
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from unix time (in s) to ms
        data['time'] = list(raw_data[self.time_channel]*1000)

        for i, j in enumerate(self.eeg_channel_indexes):
            data[self.eeg_channel_names[i]] = list(raw_data[j])

        self.database.write_data(self.id, data)

    def start(self):
        """ Extended from base class in pi_lib.py """
        # start EEG stream if not already
        if not self.streaming.is_set():
            self.board.prepare_session()
            self.board.start_stream()

    def stop(self):
        """ Extended from base class in pi_lib.py """
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass


class EEGStreamer(Streamer):
    """
    EEG Streamer class for an OpenBCI board (Cyton, Cyton+Daisy, Ganglion)
    """
    def __init__(self, *args, dev_path=None):
        """ Dev path is the device path of the dongle"""
        super().__init__(*args)

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        self.board_id = BoardIds.CYTON_DAISY_BOARD.value   # Cyton+Daisy borad ID (2)

        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)       # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency
        self.serial_port = dev_path

        #BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()
        params.serial_port = dev_path  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        # add info to send to database
        self.info['sample_rate'] = self.freq
        self.info['channels'] = ','.join(self.eeg_channel_names)

    def loop(self):
        """ Main execution loop """
        sleep(0.25)  # wait a bit for the board to collect another chunk of data
        data = {}
        for channel in self.eeg_channel_names:  # lists of channel data
            data[channel] = []

        # attempt to read from board
        # data collected in uV
        try:
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from unix time (in s) to ms
        data['time'] = list(raw_data[self.time_channel]*1000)

        for i, j in enumerate(self.eeg_channel_indexes):
            data[self.eeg_channel_names[i]] = list(raw_data[j])

        self.database.write_data(self.id, data)

    def start(self):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        # configure data collection port to avoid data chunking
        configure_port(self.serial_port)

        # start EEG session
        tries = 0
        while tries <= 5:
            tries += 1
            try:
                self.board.prepare_session()
                break
            except:
                sleep(0.1)

        if self.board.is_prepared():
            self.board.start_stream()  # start stream
        else:
            raise Exception("Failed to prepare streaming session in {}. Make sure the board is turned on.".format(self))

    def stop(self):
        """ Extended from base class in pi_lib.py """
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass


class ECGStreamer(Streamer):
    """
    Streams data from an OpenBCI board equipped with a Pulse sensor (through the analog pins)
    """
    def __init__(self, *args, dev_path):
        super().__init__(*args)

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        self.board_id = BoardIds.CYTON_BOARD.value   # Cyton board ID (0)
        self.serial_port = dev_path

        # Channels for main board output
        self.ecg_channel_indexes = BoardShim.get_ecg_channels(self.board_id)
        self.ecg_channel_names = [str(i) for i in range(len(self.ecg_channel_indexes))]  # name ECG channels by number

        # Pulse sensor data sent through 3 AUX channels instead
        self.pulse_channel_indexes = BoardShim.get_analog_channels(self.board_id)
        self.pulse_channel_names = ['pulse_0', 'pulse_1', 'pulse_2']

        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency

        self.info['sample_rate'] = self.freq
        self.info['pulse_channels'] = ','.join(self.pulse_channel_names)
        self.info['ecg_channels'] = ','.join(self.ecg_channel_names)

        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()
        params.serial_port = self.serial_port  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

    def loop(self):
        """ Main execution loop """
        sleep(0.25)  # wait a bit for the board to collect another chunk of data
        data = {}
        for channel in self.pulse_channel_names:  # lists of channel data
            data[channel] = []

        # attempt to read from board
        # data collected in uV
        try:
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from unix time (in s) to ms
        data['time'] = list(raw_data[self.time_channel]*1000)

        for i, j in enumerate(self.pulse_channel_indexes):
            data[self.pulse_channel_names[i]] = list(raw_data[j])

        for i, j in enumerate(self.ecg_channel_indexes):
            data[self.ecg_channel_names[i]] = list(raw_data[j])

        self.database.write_data(self.id, data)

    def start(self):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        if self.streaming.is_set():
            return

        # configure data collection port to avoid data chunking
        configure_port(self.serial_port)

        # start EEG session
        tries = 0
        while tries <= 5:
            tries += 1
            try:
                self.board.prepare_session()
                break
            except:
                sleep(0.1)

        if self.board.is_prepared():
            self.board.config_board('/2')  # Set board to Analog mode.
            self.board.start_stream()  # start stream
        else:
            raise Exception("Failed to prepare streaming session in {}. Make sure the board is turned on.".format(self))

    def stop(self):
        """ Extended from base class in pi_lib.py """
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass