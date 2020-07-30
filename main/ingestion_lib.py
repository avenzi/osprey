import json

from bokeh.layouts import layout
from bokeh.plotting import figure
from bokeh.palettes import viridis

from lib import ServerHandler, Request, GraphStream


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

    def INGEST(self, request):
        """ Handle image data received from Pi """
        frame = request.content  # bytes
        self.frames_received += 1
        self.frames_sent = int(request.header['frames-sent'])
        self.data_buffer.write(frame)
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
            response.add_content(self.page_html())
        elif request.path.endswith('/stream.mjpg'):  # request for a single frame
            return self.image_buffer  # return buffer to be used for multipart stream
        else:
            return False
        return response

    def page_html(self):
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
                    <p><img src="/stream.mjpg?id={id}" width="{width}" height="{height}" /></p>
                </body>
                </html>
                """.format(name=self.name, id=self.peer, width=width, height=height)
        return page


class SenseHandler(ServerHandler):
    """ Handles SenseHat stream """
    def __init__(self, *args):
        super().__init__(*args)

        self.frames_sent = 0
        self.frames_received = 0

        self.graph = None

    def INIT(self, request):
        """ Handler INIT request from client """
        self.name = request.header['name']
        self.client_name = request.header['device']

        # Create Bokeh Layout
        tools = ['save']
        humid = figure(title='Humidity', x_axis_label='time', y_axis_label='Percent', tools=tools, plot_width=600, plot_height=300)
        humid.line(x='time', y='humidity')
        press = figure(title='Pressure', x_axis_label='time', y_axis_label='Millibars', tools=tools, plot_width=600, plot_height=300)
        press.line(x='time', y='pressure')
        temp = figure(title='Temperature', x_axis_label='time', y_axis_label='Degrees Celsius', tools=tools, plot_width=600, plot_height=300)
        temp.line(x='time', y='temperature')
        orient = figure(title='Orientation', x_axis_label='time', y_axis_label='Degrees', tools=tools, plot_width=600, plot_height=300)
        orient.line(x='time', y='pitch', legend_label='Pitch', color='blue')
        orient.line(x='time', y='roll', legend_label='Roll', color='green')
        orient.line(x='time', y='yaw', legend_label='Yaw', color='red')

        lay = layout([[humid, temp], [press, orient]])
        update_url = 'http://{}/stream/update?id={}'.format(self.server.host, self.id)

        # pass layout into GraphStream object
        self.graph = GraphStream(lay, update_url, interval=50, domain=100)

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(self.encoding)  # raw JSON string
        self.graph.buffer.write(data)  # send raw JSON string to graph buffer
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
            response = self.graph.update_json()
        else:
            return False
        return response


class EEGHandler(ServerHandler):
    """ Handles SenseHat stream """
    def __init__(self, *args):
        super().__init__(*args)

        self.frames_sent = 0
        self.frames_received = 0
        self.channels = []  # list of channel name strings

        self.graph = None

    def INIT(self, request):
        """ Handler INIT request from client """
        self.name = request.header['name']
        self.client_name = request.header['device']
        self.channels = request.header['channels'].split(',')

        # Create Bokeh Layout
        tools = ['save']
        colors = viridis(len(self.channels))  # viridis color palette

        eeg_list = []
        for i in range(len(self.channels)):
            eeg = figure(title=self.channels[i], x_axis_label='time', y_axis_label='Voltage', tools=tools, plot_width=1000, plot_height=200)
            eeg.line(x='time', y=self.channels[i], color=colors[i])
            eeg_list.append(eeg)

        lay = layout(eeg_list)
        update_url = 'http://{}/stream/update?id={}'.format(self.server.host, self.id)

        # pass layout into GraphStream object
        self.graph = GraphStream(lay, update_url, interval=50, domain=1000)

    def INGEST(self, request):
        """ Handle table data received from Pi """
        data = request.content.decode(self.encoding)  # raw JSON data
        self.frames_received += 1
        self.graph.buffer.write(data)
        self.debug("Ingested EEG data (frame {})".format(self.frames_received), 3)

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
            response = self.graph.update_json()
        else:
            return False
        return response