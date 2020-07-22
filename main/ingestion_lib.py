import json
from threading import Condition
from lib import ServerHandler, Base, Request, Graph


class VideoHandler(ServerHandler):
    """ Handles video stream """
    def __init__(self, *args):
        super().__init__(*args)

        self.framerate = None
        self.resolution = None
        self.max_display_height = 600   # maximum height of video in browser

        self.frames_sent = 0
        self.frames_received = 0

    def INIT(self, request):
        """ Handler INIT request from client """
        self.name = request.header['name']           # required
        self.client_name = request.header['device']  # required

        self.framerate = request.header['framerate']
        self.resolution = tuple(int(res) for res in request.header['resolution'].split('x'))

        req = Request()  # Send START request back to client
        req.add_request('START')
        self.send(req)

    def INGEST(self, request):
        """ Handle image data received from Pi """
        frame = request.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(request.header['frames-sent'])
        self.data_buffer.write(frame)
        self.image_buffer.write(frame)  # raw data needs no modification - it's already an image
        self.debug("ingested video", 3)

    def HTML(self):
        """ Returns HTML for streaming display page in browser """
        aspect = self.resolution[0] / self.resolution[1]
        height = self.max_display_height
        width = int(aspect * height)
        page = """
                <html>
                <head><title>{name}</title></head>
                <body>
                    <h1>{name}</h1>
                    <p><a href='/index.html'>Back</a></p>
                    <p><img src="/{stream_id}/stream.mjpg" width="{width}" height="{height}" /></p>
                </body>
                </html>
                """.format(name=self.name, stream_id=self.peer, width=width, height=height)
        return page


class SenseHandler(ServerHandler):
    """ Handles SenseHat stream """
    def __init__(self, *args):
        super().__init__(*args)

        self.framerate = None
        self.resolution = None
        self.max_display_width = 1000

        self.frames_sent = 0
        self.frames_received = 0

        self.graph = None  # dynamic graph object
        self.graph_lock = Condition()

    def INIT(self, request):
        """ Handler INIT request from client """
        self.name = request.header['name']
        self.client_name = request.header['device']

        self.frames = int(request.header['frames'])  # how many frames are sent in each request

        req = Request()  # Send START request back to client
        req.add_request('START')
        self.send(req)

    def INGEST(self, request):
        """ Handle table data received from Pi """
        if not self.graph:  # initialize plots
            self.graph = Graph(2, 2, self.frames*10)  # 2x2 subplots, domain 10 times the frame update size
            self.graph.ax[0, 0].set_title("Humidity")
            self.graph.ax[0, 0].add_lines("humid")
            self.graph.ax[0, 0].set_ylabel("Percent")
            self.graph.ax[0, 0].set_mode("max")

            self.graph.ax[1, 0].set_title("Pressure")
            self.graph.ax[1, 0].add_lines("press")
            self.graph.ax[1, 0].set_ylabel("Millibars")
            self.graph.ax[1, 0].set_mode("max")

            self.graph.ax[0, 1].set_title("Temperature")
            self.graph.ax[0, 1].add_lines("temp")
            self.graph.ax[0, 1].set_ylabel("Degrees Celsius")
            self.graph.ax[0, 1].set_mode("max")

            self.graph.ax[1, 1].set_title("Orientation")
            self.graph.ax[1, 1].add_lines("roll", "pitch", "yaw")
            self.graph.ax[1, 1].add_legend()
            self.graph.ax[1, 1].set_mode("fixed", (0, 360))

        data = request.content.decode(self.encoding)  # decode data
        data = json.loads(data)  # convert to object from json string
        self.frames_received += 1
        with self.graph_lock:
            # get data from decoded dictionary
            time = data['time']
            self.graph.ax[0, 0].add_data('humid', time, data['humidity'])
            self.graph.ax[1, 0].add_data('press', time, data['pressure'])
            self.graph.ax[0, 1].add_data('temp', time, data['temperature'])
            self.graph.ax[1, 1].add_data('roll', time, data['roll'])
            self.graph.ax[1, 1].add_data('pitch', time, data['pitch'])
            self.graph.ax[1, 1].add_data('yaw', time, data['yaw'])
            self.graph.save(self.image_buffer)  # save plots to image buffer
        self.debug("Ingested sense data", 3)

    def HTML(self):
        """ Returns HTML for streaming display page in browser """
        aspect = self.graph.aspect['height'] / self.graph.aspect['width']
        width = self.max_display_width
        height = int(aspect * width)
        page = """
                <html>
                <head><title>{name}</title></head>
                <body>
                    <h1>{name}</h1>
                    <p><a href='/index.html'>Back</a></p>
                    <p><img src="/{stream_id}/stream.mjpg" width="{width}" height="{height}" /></p>
                </body>
                </html>
                """.format(name=self.name, stream_id=self.peer, width=width, height=height)
        return page

