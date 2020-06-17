import io
import json
import struct
import socket
from PIL import Image
from time import strftime
from requests import get


def encode_json(obj, encoding):
    """ transform a dictionary into encoded json format """
    return json.dumps(obj, ensure_ascii=False).encode(encoding)


def decode_json(json_bytes, encoding):
    """ decode json bytes into a dictionary """
    wrap = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
    obj = json.load(wrap)
    wrap.close()
    return obj


class StreamHandler:
    """
    Handler for the socket and TCP stream for the server
    """
    def __init__(self, port, ip='', debug=False):
        self.ip = ip         # host ip
        self.port = port     # host port
        self.pi_ip = None    # RasPi ip
        self.pi_port = None  # RasPi port

        self.socket = None   # socket object

        self.in_buffer = b''  # intake buffer as bytes object
        self.proto = None     # proto-header, denoting the size of the actual header
        self.header = None    # header
        self.content = None   # message content

        self.number_received = 0       # number of images received
        self.number_sent = 0           # number of images sent from the pi (sent in header)

        self.exit = False   # flag to signal clean termination
        self.debug = debug  # activates full output

    def stream(self):
        """
        Create and connect to socket,
        then read from the TCP continually,
        disconnecting on error.
        """
        self.connect()

        msg = False  # flag for displaying the streaming notification
        try:
            while True:
                self.read()
                if self.exit:
                    break
                if self.number_received == 1 and not msg:
                    msg = True
                    print("Streaming...")
        finally:
            self.disconnect()
            print("> Frames Received: {}/{}".format(self.number_received, self.number_sent))

    def connect(self):
        """ Create and connect to socket via given address """
        print("IP:", get('http://ipinfo.io/ip').text.strip())  # display this machine's IP

        try:   # Create initial socket object
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
            print("> Socket Created...")
        except Exception as e:
            raise Exception("Failed to create socket: \n{}".format(e))

        try:  # Bind socket to ip and port
            sock.bind((self.ip, self.port))
            print("> Socket Bound...")
        except Exception as e:
            raise Exception("Failed to bind socket to {}:{} \n{}".format(self.ip, self.port, e))

        try:  # Listen for connection
            print("> Listening for Connection on {}:{}".format(self.ip, self.port))
            sock.listen()
        except Exception as e:
            raise Exception("Error while listening on {}:{} \n{}".format(self.ip, self.port, e))

        try:  # Accept connection. Accept() returns a new socket object that can send and receive data.
            self.socket, (self.pi_ip, self.pi_port) = sock.accept()
            print("> Accepted Connection From {}:{}".format(self.pi_ip, self.pi_port))
        except Exception as e:
            raise Exception("Failed to accept connection from {}:{} \n{}".format(self.pi_ip, self.pi_port, e))

    def read(self):
        """ read from the TCP stream one time """
        try:
            data = self.socket.recv(4096)  # receive data from pi
        except BlockingIOError:  # Temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:  # if received data
                self.in_buffer += data  # append to in-buffer
            else:  # stream disconnected
                print("> Collection Stream Disconnected ({}:{})".format(self.pi_ip, self.pi_port))
                self.exit = True
                return

        if self.proto is None:      # haven't gotten proto yet
            self.parse_proto()
        elif self.header is None:   # haven't gotten header yet
            self.parse_header()
        elif self.content is None:  # haven't gotten content yet
            self.parse_content()

    def parse_proto(self):
        """ Parse the proto-header from the start of the buffer, stores in self.proto """
        proto_len = 2      # length of proto-header in bytes

        # Complete proto not yet received
        if len(self.in_buffer) < proto_len:
            return

        self.proto = struct.unpack('>H', self.in_buffer[:proto_len])[0]  # parse proto (big unsigned short)
        self.in_buffer = self.in_buffer[proto_len:]  # move down the buffer
        self.log("Got proto:", self.proto)

    def parse_header(self):
        """ Parse the header from the start of the buffer, stores in self.header """
        header_len = self.proto

        # Complete header not yet received
        if len(self.in_buffer) < self.proto:
            return

        self.header = decode_json(self.in_buffer[:header_len], 'utf-8')  # parse header
        self.in_buffer = self.in_buffer[header_len:]  # move down the buffer
        self.log("Got header:", self.header)

        # validate header
        for info in ('length', 'number'):
            if info not in self.header:
                raise ValueError('Missing required header "{}"'.format(info))

    def parse_content(self):
        """ Parse content from the start of the buffer """
        content_len = self.header["length"]

        # Complete content not yet received
        if len(self.in_buffer) < content_len:
            return

        data = self.in_buffer[:content_len]  # parse content
        self.in_buffer = self.in_buffer[content_len:]  # move down buffer

        # Decode image data
        stream = io.BytesIO(data)  # convert received data into bytesIO object for PIL
        img = Image.open(stream)  # open object as JPEG
        self.log("Received image. Length: {}, Size: {}".format(len(data), img.size))
        # img.save("./images/img_{}.png".format(strftime('%Y-%m-%d_%H-%M-%S')))  # save image

        self.number_received += 1  # received another image
        self.number_sent = self.header['number']  # update number sent from pi
        self.reset()      # reset class attributes to prepare for another image

    def reset(self):
        """ Reset all message variables, ready to receive another """
        self.proto = None
        self.header = None
        self.content = None
        self.log("Reset proto, header, and content")

    def disconnect(self):
        """ Disconnect """
        self.socket.close()
        print("> Connection Closed")

    def log(self, *args):
        """ Prints message if debug is set to True """
        if self.debug:
            print(*args)
