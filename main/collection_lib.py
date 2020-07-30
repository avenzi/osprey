import time
import msgpack as mp
import json
from lib import ClientHandler, Request
try:
    import picamera
except:
    print("Unable to import PiCamera")
try:
    from sense_hat import SenseHat
except:
    print("Unable to import SenseHat")
try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
except:
    print("Unable to import BrainFlow.")


class VideoHandler(ClientHandler):
    def __init__(self, *args):
        super().__init__(*args)

        self.name = "Video Stream"

        self.camera = None             # picam object
        self.resolution = '640x480'  # resolution of stream
        self.framerate = 24            # camera framerate

        self.frames_sent = 0    # number of frames sent
        self.time = 0           # time of START

        self.init()

    def init(self):
        """
        Send sign-on request to server
        Gives the server necessary information about this connection.
        Server will respond with the START request.
        """
        req = Request()  # new request
        req.add_request('INIT')                     # call INIT method on server handler
        req.add_header('device', self.client.name)  # device name (in config.json)
        req.add_header('name', self.name)           # stream name
        req.add_header('class', "VideoHandler")     # Name of handler class in ingestion_lib to be used to on the server

        req.add_header('resolution', self.resolution)
        req.add_header('framerate', self.framerate)
        self.send(req)   # send request

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("Video Stream already Started")
            return
        self.streaming = True

        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.camera.start_recording(self.data_buffer, format='mjpeg')
        time.sleep(2)  # let camera warm up for a sec. Does weird stuff otherwise.
        self.time = time.time()  # mark start time
        self.log("Started Video Stream")

        req = Request()
        req.add_request("INGEST")

        do_separate = True  # for testing purposes - whether to use separate requests for each frame rather than a multipart stream.
        if do_separate:
            while self.streaming:
                data = self.data_buffer.read()
                self.frames_sent += 1
                req.add_header('frames-sent', self.frames_sent)
                req.add_header('time', time.time()-self.time)  # time since start
                req.add_content(data)
                self.send(req)
        else:  # for multipart streaming, as if to a browser. Not currently stable.
            self.send_multipart(self.data_buffer, req)

    def STOP(self, request):
        """ Request method STOP """
        self.streaming = False
        self.camera.stop_recording()
        self.log("Stopped Recording: {}".format(self.date()))
        self.log("Stopped Stream.")


class SenseHandler(ClientHandler):
    def __init__(self, *args):
        super().__init__(*args)

        self.name = "Sense Stream"

        self.sense = SenseHat()   # sense hat object
        self.frames = 1           # how many frames are in each request

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

        self.init()

    def init(self):
        """
        Send sign-on request to server
        Gives the server necessary information about this connection.
        Server will respond with the START request.
        """
        req = Request()
        req.add_request('INIT')
        req.add_header('device', self.client.name)  # device name (in config.json)
        req.add_header('name', self.name)           # stream name
        req.add_header('class', "SenseHandler")  # Name of handler class to be used to on the server
        self.send(req)

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("Sense Stream already Started")
            return
        self.streaming = True

        # collect sensor data
        self.time = time.time()
        self.log("Started Sense Stream...")

        req = Request()
        req.add_request("INGEST")

        self.sense.set_imu_config(True, True, True)  # enable compas, gyro, and accelerometer to calculate orientation

        do_separate = True  # for testing purposes - whether to use separate requests for each frame rather than a multipart stream.
        if do_separate:
            while self.streaming:
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
                req.add_header('frames-sent', self.frames_sent)
                req.add_content(data)
                self.send(req)
        else:  # for multipart streaming, as if to a browser. Not currently stable.
            self.throw("no multipart made for data")

    def STOP(self, request):
        """ Request method STOP """
        self.streaming = False
        self.log("Stopped Recording SenseHat: {}".format(self.date()))
        self.log("Stopped Stream.")


class EEGHandler(ClientHandler):
    def __init__(self, *args):
        super().__init__(*args)

        self.name = "EEG Stream"

        self.board = None  # Cyton board object
        self.board_id = BoardIds.CYTON_DAISY_BOARD.value   # board id according to BarinFlow Docs. It's 2.
        self.eeg_channel_indexes = BoardShim.get_eeg_channels(self.board_id)  # list of EEG channel indexes
        self.eeg_channel_names = BoardShim.get_eeg_names(self.board_id)       # list of EEG channel names
        self.time_channel = BoardShim.get_timestamp_channel(self.board_id)    # index of timestamp channel
        self.freq = BoardShim.get_sampling_rate(self.board_id)                # sample frequency
        # BoardShim.enable_dev_board_logger()
        BoardShim.disable_board_logger()  # disable logger

        self.frames_sent = 0    # number of frames sent
        self.time = 0  # time of START

        self.init()

    def init(self):
        """
        Send sign-on request to server
        Gives the server necessary information about this connection.
        Server will respond with the START request.
        """
        req = Request()
        req.add_request('INIT')
        req.add_header('device', self.client.name)  # device name (in config.json)
        req.add_header('name', self.name)           # stream name
        req.add_header('class', "EEGHandler")  # Name of handler class to be used to on the server

        req.add_header('channels', ','.join(self.eeg_channel_names))

        self.send(req)

    def START(self, request):
        """ Start Streaming continually."""
        if self.streaming:
            self.log("EEG Stream already Started")
            return
        self.streaming = True

        # collect sensor data
        params = BrainFlowInputParams()
        params.serial_port = '/dev/ttyUSB0'  # serial port of dongle
        self.board = BoardShim(self.board_id, params)
        self.board.prepare_session()
        self.board.start_stream()

        self.time = time.time()
        self.log("Started EEG Stream...")
        req = Request()
        req.add_request("INGEST")

        do_separate = True  # for testing purposes - whether to use separate requests for each frame rather than a multipart stream.
        if do_separate:
            while self.streaming:
                data = {}
                data['time'] = []  # time data
                for channel in self.eeg_channel_names:  # lists of channel data
                    data[channel] = []

                raw_data = self.board.get_board_data()
                data['time'] = list(raw_data[self.time_channel])

                i = 0
                for j in self.eeg_channel_indexes:
                    data[self.eeg_channel_names[i]] = list(raw_data[j]/1000000)  # convert from uV to V
                    i += 1

                data = json.dumps(data).encode(self.encoding)
                self.frames_sent += 1
                req.add_header('frames-sent', self.frames_sent)
                req.add_content(data)
                self.send(req)
                time.sleep(0.2)
        else:  # for multipart streaming, as if to a browser. Not currently stable.
            self.throw("no multipart made for data")

    def STOP(self, request):
        """ Request method STOP """
        self.streaming = False
        self.log("Stopped Recording SenseHat: {}".format(self.date()))
        self.log("Stopped Stream.")

        self.board.stop_stream()
        self.board.release_session()
