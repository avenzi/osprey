import time
import msgpack as mp
import json
from lib import Streamer, Request, DataBuffer


class VideoStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'VideoHandler'

        self.camera = None             # picam object
        self.resolution = '640x480'  # resolution of stream
        self.framerate = 24            # camera framerate

        self.frames_sent = 0    # number of frames sent
        self.time = 0           # time of START

        self.data_buffer = DataBuffer()  # buffer to hold data as it is collected from the picam
        self.streaming = False  # flag to start and stop stream

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("Video Stream already Started")
            return
        self.streaming = True

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
        self.log("Started Video Stream")

        # Send INGEST requests with image data
        resp = Request()  # new response
        resp.add_request("INGEST")

        while self.streaming and not request.origin.exit:
            data = self.data_buffer.read()
            self.frames_sent += 1
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_header('time', time.time()-self.time)  # time since start
            resp.add_content(data)
            self.send(resp, request.origin)  # send INGEST request back

    def STOP(self, request):
        """ Request method STOP """
        self.streaming = False
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(self.date()))
        self.log("Stopped Stream.")


class SenseStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'SenseHandler'

        from sense_hat import SenseHat
        self.sense = SenseHat()   # sense hat object
        self.frames = 1           # how many frames are in each request

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

        self.streaming = False  # flag to start and stop stream

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("Sense Stream already Started")
            return
        self.streaming = True

        # get start time
        self.time = time.time()
        self.log("Started Sense Stream...")

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
        """ Request method STOP """
        self.streaming = False
        self.log("Stopped Recording SenseHat: {}".format(self.date()))
        self.log("Stopped Stream.")


class EEGStreamer(Streamer):
    def __init__(self):
        super().__init__()
        self.handler = 'EEGHandler'

        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
        self.board_id = BoardIds.CYTON_DAISY_BOARD.value   # board id according to BarinFlow Docs. It's 2.
        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)       # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)                # sample frequency
        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        params = BrainFlowInputParams()
        params.serial_port = '/dev/ttyUSB0'  # serial port of dongle
        self.board = BoardShim(self.board_id, params)  # board object

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

        self.streaming = False  # flag to start and stop stream

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("EEG Stream already Started")
            return
        self.streaming = True

        # First send some initial information
        req = Request()
        req.add_request('INIT')
        req.add_header('channels', ','.join(self.eeg_channel_names))
        self.send(req, request.origin)

        # start EEG session
        self.board.prepare_session()
        self.board.start_stream()

        # get start time
        self.time = time.time()
        self.log("Started EEG Stream...")

        # continually collect sensor data
        resp = Request()  # new response
        resp.add_request("INGEST")
        while self.streaming and not request.origin.exit:
            data = {}
            data['time'] = []  # time data
            for channel in self.eeg_channel_names:  # lists of channel data
                data[channel] = []

            raw_data = self.board.get_board_data()
            data['time'] = list(raw_data[self.time_channel])

            for i, j in enumerate(self.eeg_channel_indexes):
                data[self.eeg_channel_names[i]] = list(raw_data[j]/1000000)  # convert from uV to V

            data = json.dumps(data).encode(self.encoding)
            self.frames_sent += 1
            resp.add_header('frames-sent', self.frames_sent)
            resp.add_content(data)
            self.send(resp, request.origin)
            time.sleep(0.2)  # wait a bit for the board to collect another chunk of data

    def STOP(self, request):
        """ Request method STOP """
        self.streaming = False
        self.log("Stopped Recording SenseHat: {}".format(self.date()))
        self.log("Stopped Stream.")

        self.board.stop_stream()
        self.board.release_session()
