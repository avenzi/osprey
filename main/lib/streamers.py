import time
import json

from pi_lib import Streamer, Request
from lib import DataBuffer


class VideoStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'VideoHandler'

        self.camera = None             # picam object
        self.resolution = '200x200'  # resolution of stream
        self.framerate = 10            # camera framerate

        self.frames_sent = 0    # number of frames sent
        self.time = 0           # time of START

        self.data_buffer = DataBuffer()  # buffer to hold data as it is collected from the picam

    def START(self, request):
        """
        Request method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        super().START(request)  # extend

        # First send some initial information
        init_req = Request()  # new request
        init_req.add_request('INIT')  # call INIT method on server handler
        init_req.add_header('resolution', self.resolution)
        init_req.add_header('framerate', self.framerate)
        self.send(init_req, request.origin)  # send init request back

        # Start stream
        import picamera
        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.camera.start_recording(self.data_buffer, format='mjpeg')
        time.sleep(2)  # let camera warm up for a sec. Does weird stuff otherwise.
        self.time = time.time()  # mark start time

        # Send INGEST requests with image data
        resp = Request()  # new response
        resp.add_request("INGEST")

        lock = self.data_buffer.get_ticket()
        while self.streaming and not request.origin.exit:
            data = self.data_buffer.read(lock, block=True)
            self.frames_sent += 1
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_header('time', time.time()-self.time)  # time since start
            resp.add_content(data)
            self.send(resp, request.origin)  # send INGEST request back

    def STOP(self, request):
        """
        Request method STOP
        Extended from the base class in pi_lib.py
        """
        super().STOP(request)  # extend
        self.camera.stop_recording()


class SenseStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'SenseHandler'

        from sense_hat import SenseHat
        self.sense = SenseHat()   # sense hat object
        self.frames = 1           # how many frames are in each request

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

    def START(self, request):
        """
        Request method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        super().START(request)  # extend

        # get start time
        self.time = time.time()

        resp = Request()  # new INGEST request
        resp.add_request("INGEST")

        # enable compass, gyro, and accelerometer to calculate orientation
        self.sense.set_imu_config(True, True, True)

        # continually collect sensor data and sent them to the server
        while self.streaming and not request.origin.exit:
            data = {'time': [], 'humidity': [], 'pressure': [], 'temperature': [], 'pitch': [], 'roll': [], 'yaw': []}
            for i in range(self.frames):
                roll, pitch, yaw = self.sense.get_orientation_degrees().values()
                data['humidity'].append(self.sense.get_humidity())
                data['pressure'].append(self.sense.get_pressure())
                data['temperature'].append((self.sense.get_temperature_from_humidity() + self.sense.get_temperature_from_pressure())/2)
                data['roll'].append(roll)
                data['pitch'].append(pitch)
                data['yaw'].append(yaw)
                data['time'].append(time.time()-self.time)

            data = json.dumps(data).encode(self.encoding)  # send as JSON string
            self.frames_sent += self.frames
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_content(data)
            self.send(resp, request.origin)

    def STOP(self, request):
        """
        Request method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # extend


class ECGStreamer(Streamer):
    """
    ECG Streamer class for an OpenBCI board (Cyton, Cyton+Daisy, Ganglion)
    """
    def __init__(self):
        super().__init__()
        self.handler = 'ECGHandler'
        synth = False  # whether to use the BrainFlow Synthetic board (for testing and whatnot)

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        if synth:
            self.board_id = BoardIds.SYNTHETIC_BOARD.value  # synthetic board (-1)
        else:
            self.board_id = BoardIds.CYTON_BOARD.value   # Cyton board ID (0)

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

        if not synth:
            params.serial_port = '/dev/ttyUSB1'  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

    def START(self, request):
        """
        Request method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        super().START(request)  # extend

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

        # get start time
        self.time = time.time()

        # First send some initial information
        req = Request()
        req.add_request('INIT')
        req.add_header('sample_rate', self.freq)
        req.add_header('ecg_channels', ','.join(self.ecg_channel_names+self.pulse_channel_names))
        req.add_header('pulse_channels', ','.join(self.pulse_channel_names))
        self.send(req, request.origin)

        # continually collect sensor data
        resp = Request()  # new response
        resp.add_request("INGEST")
        while self.streaming and not request.origin.exit:
            time.sleep(0.2)  # wait a bit for the board to collect another chunk of data
            raw_data = self.board.get_board_data()

            # convert from epoch time to relative time since session start
            data = {'time': list(raw_data[self.time_channel] - self.time)}
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
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_content(data)
            self.send(resp, request.origin)

    def STOP(self, request):
        """
        Request method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # extend

        self.board.stop_stream()
        self.board.release_session()


class EEGStreamer(Streamer):
    """
    EEG Streamer class for an OpenBCI board (Cyton, Cyton+Daisy, Ganglion)
    """
    def __init__(self):
        super().__init__()
        self.handler = 'EEGHandler'
        synth = False  # whether to use the BrainFlow Synthetic board (for testing and whatnot)

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        if synth:
            self.board_id = BoardIds.SYNTHETIC_BOARD.value  # synthetic board (-1)
        else:
            self.board_id = BoardIds.CYTON_DAISY_BOARD.value   # Cyton+Daisy borad ID (2)

        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)       # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)  # sample frequency

        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()

        if not synth:
            params.serial_port = '/dev/ttyUSB0'  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

    def START(self, request):
        """
        Request method START
        Start Streaming continually
        Extended from base class in pi_lib.py
        """
        super().START(request)  # extend

        # First send some initial information
        req = Request()
        req.add_request('INIT')
        req.add_header('sample_rate', self.freq)
        req.add_header('channels', ','.join(self.eeg_channel_names))
        self.send(req, request.origin)

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

        # get start time
        self.time = time.time()

        # continually collect sensor data
        resp = Request()  # new response
        resp.add_request("INGEST")
        while self.streaming and not request.origin.exit:
            time.sleep(0.2)  # wait a bit for the board to collect another chunk of data
            data = {}
            for channel in self.eeg_channel_names:  # lists of channel data
                data[channel] = []

            raw_data = self.board.get_board_data()

            # convert from epoch time to relative time since session start
            data['time'] = list(raw_data[self.time_channel]-self.time)

            for i, j in enumerate(self.eeg_channel_indexes):
                data[self.eeg_channel_names[i]] = list(raw_data[j]/1000000)  # convert from uV to V

            data = json.dumps(data).encode(self.encoding)
            self.frames_sent += 1
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_content(data)
            self.send(resp, request.origin)

    def STOP(self, request):
        """
        Request method STOP
        Extended from base class in pi_lib.py
        """
        super().STOP(request)  # extend

        self.board.stop_stream()
        self.board.release_session()
