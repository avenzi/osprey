import time
import json
import msgpack
import os
from io import BytesIO

from ..lib import Base
from .pi_lib import Streamer, HTTPRequest, configure_port, CONFIG_PATH, PicamOutput


class LogStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'LogHandler'

        with open(CONFIG_PATH) as config_file:
            config = json.load(config_file)
        self.log_path = config.get('LOG_PATH') + '/log.log'
        self.client_name = config.get('NAME')

    def loop(self):
        """ Main execution loop """
        time.sleep(10)  # send every 10 seconds
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
    def __init__(self):
        super().__init__()
        self.handler = 'VideoHandler'

        self.camera = None
        self.resolution = '300x300'  # resolution of stream
        self.framerate = 20            # camera framerate

        self.frames_sent = 0    # number of frames sent
        self.start_time = 0           # time of START

        self.picam_buffer = PicamOutput()  # buffer to hold images from the Picam

    def loop(self):
        """
        Main execution loop
        """
        if not self.camera.frame.complete or self.camera.frame.frame_type == self.sps:
            return
        image = self.picam_buffer.read()  # get most recent frame
        self.frames_sent += 1

        resp = HTTPRequest("INGEST")  # new request
        resp.add_header('frames-sent', self.frames_sent)
        resp.add_header('time', self.time())  # time since start
        resp.add_content(image)

        #t2 = time.time()
        self.send(resp)  # send INGEST request back to source
        #t3 = time.time()
        #self.log("sent {} in {:.3}".format(len(image), t3-t2))

    def START(self, request):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        if self.streaming.is_set():
            return
        # First send initial information
        init_req = HTTPRequest()  # new request
        init_req.add_request('INIT')  # call INIT method on server handler
        init_req.add_header('resolution', self.resolution)
        init_req.add_header('framerate', self.framerate)
        self.send(init_req)

        # set up camera
        from picamera import PiCamera, PiVideoFrameType
        self.sps = PiVideoFrameType.sps_header
        self.camera = PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.camera.start_recording(self.picam_buffer,
            format='h264', quality=25, profile='constrained', level='4.2',
            intra_period=self.framerate, intra_refresh='both', inline_headers=True, sps_timing=True
        )
        time.sleep(2)  # let camera warm up for a sec. Does weird stuff otherwise.
        super().START(request)  # Start main loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from the base class in pi_lib.py
        """
        super().STOP(request)  # Stop main loop
        try:
            self.camera.stop_recording()
            self.camera.close()  # close camera resources
        except:
            pass


class SenseStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'SenseHandler'

        from sense_hat import SenseHat
        self.sense = SenseHat()   # sense hat object
        self.frames = 1           # how many frames are in each request

        self.frames_sent = 0    # number of frames sent

    def loop(self):
        """ Maine execution loop """
        data = {'time': [], 'humidity': [], 'pressure': [], 'temperature': [], 'pitch': [], 'roll': [], 'yaw': []}
        for i in range(self.frames):
            roll, pitch, yaw = self.sense.get_orientation_degrees().values()
            data['humidity'].append(self.sense.get_humidity())
            data['pressure'].append(self.sense.get_pressure())
            data['temperature'].append((self.sense.get_temperature_from_humidity() + self.sense.get_temperature_from_pressure()) / 2)
            data['roll'].append(roll)
            data['pitch'].append(pitch)
            data['yaw'].append(yaw)
            data['time'].append(self.time())

        resp = HTTPRequest()  # new INGEST request
        resp.add_request("INGEST")
        data = json.dumps(data).encode(self.encoding)  # send as JSON string
        self.frames_sent += self.frames
        resp.add_header('frames-sent', self.frames_sent)
        resp.add_content(data)
        self.send(resp)

    def START(self, request):
        """
        HTTPRequest method START
        Extended from base class in pi_lib.py
        """
        # enable compass, gyro, and accelerometer to calculate orientation
        self.sense.set_imu_config(True, True, True)

        super().START(request)  # start main loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # stop main loop


class EEGStreamer(Streamer):
    """
    EEG Streamer class for an OpenBCI board (Cyton, Cyton+Daisy, Ganglion)
    """
    def __init__(self):
        super().__init__()
        self.handler = 'EEGHandler'

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        self.board_id = BoardIds.CYTON_DAISY_BOARD.value   # Cyton+Daisy borad ID (2)
        with open(CONFIG_PATH) as config_file:  # get device path
            config = json.load(config_file)
        self.serial_port = config['VCP'][self.__class__.__name__]

        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)       # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency

        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()

        params.serial_port = self.serial_port  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        self.frames_sent = 0    # number of frames sent

    def loop(self):
        """ Main execution loop """
        time.sleep(0.2)  # wait a bit for the board to collect another chunk of data
        data = {}
        for channel in self.eeg_channel_names:  # lists of channel data
            data[channel] = []

        try:  # attempt to read from board
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from epoch time to relative time since session start
        data['time'] = list(raw_data[self.time_channel] - self.start_time)

        for i, j in enumerate(self.eeg_channel_indexes):
            data[self.eeg_channel_names[i]] = list(raw_data[j] / 1000000)  # convert from uV to V

        data = json.dumps(data).encode(self.encoding)
        self.frames_sent += 1

        resp = HTTPRequest()  # new response
        resp.add_request("INGEST")
        resp.add_header('frames-sent', self.frames_sent)
        resp.add_content(data)
        self.send(resp)

    def START(self, request):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        # configure data collection ports to avoid data chunking
        configure_port(self.serial_port)

        # start EEG session
        tries = 0
        while tries <= 5:
            tries += 1
            try:
                self.board.prepare_session()
                break
            except:
                time.sleep(0.1)

        if self.board.is_prepared():
            self.board.start_stream()  # start stream
        else:
            self.throw("Failed to prepare streaming session in {}. Make sure the board is turned on.".format(self.name), trace=False)
            return

        # First send some initial information
        req = HTTPRequest()
        req.add_request('INIT')
        req.add_header('sample_rate', self.freq)
        req.add_header('channels', ','.join(self.eeg_channel_names))
        self.send(req, request.origin)

        super().START(request)  # start main loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # extend
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass


class ECGStreamer(Streamer):
    """
    ECG Streamer class for an OpenBCI board (Cyton, Cyton+Daisy, Ganglion)
    """
    def __init__(self):
        super().__init__()
        self.handler = 'ECGHandler'

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        self.board_id = BoardIds.CYTON_BOARD.value   # Cyton board ID (0)

        with open(CONFIG_PATH) as config_file:  # get device path
            config = json.load(config_file)
        self.serial_port = config['VCP'][self.__class__.__name__]

        # Note that the channels returned would be for EEG channels
        self.ecg_channel_indexes = BoardShim.get_ecg_channels(self.board_id)
        self.ecg_channel_names = [str(i) for i in range(len(self.ecg_channel_indexes))]  # list of ECG channel names

        # Pulse sensor data sent through 3 AUX channels
        self.pulse_channel_indexes = BoardShim.get_analog_channels(self.board_id)
        self.pulse_channel_names = ['pulse_0', 'pulse_1', 'pulse_2']

        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency

        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()

        params.serial_port = self.serial_port  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        self.frames_sent = 0    # number of frames sent

    def loop(self):
        """ Main execution loop """
        time.sleep(0.2)  # wait a bit for the board to collect another chunk of data

        try:  # attempt to read from board
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from epoch time to relative time since session start
        data = {'time': list(raw_data[self.time_channel] - self.start_time)}
        for channel in self.ecg_channel_names:  # lists of channel data
            data[channel] = []

        # add ECG data
        for i, j in enumerate(self.ecg_channel_indexes):
            data[self.ecg_channel_names[i]] = list(raw_data[j])

        # add Pulse data
        for i, j in enumerate(self.pulse_channel_indexes):
            data[self.pulse_channel_names[i]] = list(raw_data[j])

        data = json.dumps(data).encode(self.encoding)
        self.frames_sent += 1

        resp = HTTPRequest()  # new response
        resp.add_request("INGEST")
        resp.add_header('frames-sent', self.frames_sent)
        resp.add_content(data)
        self.send(resp)

    def START(self, request):
        """
        HTTPRequest method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        # configure data collection ports to avoid data chunking
        configure_port(self.serial_port)

        # start ECG session
        tries = 0
        while tries <= 5:
            tries += 1
            try:
                self.board.prepare_session()
                break
            except:
                time.sleep(0.1)

        if self.board.is_prepared():
            self.board.config_board('/2')  # Set board to Analog mode.
            self.board.start_stream()  # start stream
        else:
            self.throw("Failed to prepare streaming session in {}. Make sure the board is turned on.".format(self.name), trace=False)
            return

        # First send some initial information
        req = HTTPRequest()
        req.add_request('INIT')
        req.add_header('sample_rate', self.freq)
        req.add_header('ecg_channels', ','.join(self.ecg_channel_names+self.pulse_channel_names))
        req.add_header('pulse_channels', ','.join(self.pulse_channel_names))
        self.send(req, request.origin)

        super().START(request)  # start main execution loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # stop execution loop
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass


class SynthEEGStreamer(Streamer):
    """
    Synthetic EEG streamer class for testing
    """
    def __init__(self):
        super().__init__()
        self.handler = 'EEGHandler'

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

        self.frames_sent = 0  # number of frames sent

    def loop(self):
        """ Main execution loop """
        time.sleep(0.25)  # wait a bit for the board to collect another chunk of data
        data = {}
        for channel in self.eeg_channel_names:  # lists of channel data
            data[channel] = []

        try:  # attempt to read from board
            raw_data = self.board.get_board_data()
        except Exception as e:
            return

        # convert from epoch time to relative time since session start
        data['time'] = list(raw_data[self.time_channel] - self.start_time)

        for i, j in enumerate(self.eeg_channel_indexes):
            data[self.eeg_channel_names[i]] = list(raw_data[j] / 1000000)  # convert from uV to V

        data = msgpack.packb(data)  # pack dict object
        self.frames_sent += 1

        resp = HTTPRequest()  # new response
        resp.add_request("INGEST")
        resp.add_header('frames-sent', self.frames_sent)
        resp.add_header('time', time.time())
        resp.add_content(data)

        #t0 = time.time()
        self.send(resp)
        #t1 = time.time()
        #self.log("sent {} in {:.3}".format(len(data), t1-t0))

    def START(self, request):
        """
        HTTPRequest method START
        Extended from base class in pi_lib.py
        """
        # start EEG stream
        self.board.prepare_session()
        self.board.start_stream()

        # First send some initial information
        req = HTTPRequest()
        req.add_request('INIT')
        req.add_header('sample_rate', self.freq)
        req.add_header('channels', ','.join(self.eeg_channel_names))
        self.send(req, request.origin)

        super().START(request)  # start main loop

    def STOP(self, request):
        """
        HTTPRequest method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # stop main loop
        try:
            self.board.stop_stream()
            self.board.release_session()
        except:
            pass


