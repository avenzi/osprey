import io
import json
import struct
import socket
from PIL import Image
from time import strftime


def encode_json(obj, encoding):
    """ transform a dictionary into encoded json format """
    return json.dumps(obj, ensure_ascii=False).encode(encoding)


def decode_json(json_bytes, encoding):
    """ decode json bytes into a dictionary """
    wrap = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
    obj = json.load(wrap)
    wrap.close()
    return obj


class ServerHandler:
    """
    Handler for the socket and TCP stream for the server
    """
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = None

        self.in_buffer = b''  # intake buffer as bytes object
        self.proto = None     # proto-header, denoting the size of the actual header
        self.header = None    # header
        self.content = None   # message content

        self.num = 0   # number of images received

    def connect(self):
        """ Create and connect to socket via given address. """
        try:   # create socket object
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
            print("Socket Created")
        except Exception as e:
            raise Exception("Failed to create socket: \n{}".format(e))

        try:  # connect socket to given address
            self.socket.connect((self.ip, self.port))
            print("Socket Connected")
        except Exception as e:
            raise Exception("Failed to connect to socket on {}:{} \n{}".format(self.ip, self.port, e))

    def read(self):
        """ read from the TCP stream """
        try:
            data = self.socket.recv(4096)  # receive data from pi
        except BlockingIOError:  # Temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:  # if received data
                self.in_buffer += data  # append to in-buffer
            else:
                raise RuntimeError('Peer closed.')

        if self.proto is None:      # haven't gotten proto yet
            self.parse_proto()
        elif self.header is None:   # haven't gotten header yet
            self.parse_header()
        elif self.content is None:  # haven't gotten content yet
            self.parse_content()

    def parse_proto(self):
        """ Parse the proto-header from the start of the buffer """
        proto_len = 2      # length of proto-header

        # Complete proto not yet received
        if len(self.in_buffer) < proto_len:
            return

        self.proto = struct.unpack('>H', self.in_buffer[:proto_len])[0]  # parse proto (big unsigned short)
        self.in_buffer = self.in_buffer[proto_len:]  # move down the buffer
        # print("Got proto:", self.proto)

    def parse_header(self):
        """ Parse the header from the start of the buffer """
        header_len = self.proto

        # Complete header not yet received
        if len(self.in_buffer) < self.proto:
            return

        self.header = decode_json(self.in_buffer[:header_len], 'utf-8')  # parse header
        self.in_buffer = self.in_buffer[header_len:]  # move down the buffer
        # print("Got header:", self.header)

        # validate header
        for info in ("byteorder", "length", "type", "encoding"):
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

        # handle content
        if self.header['type'] == 'text/json':
            encoding = self.header["encoding"]
            self.content = decode_json(data, encoding)
            # print("Received text response from [{}:{}]: \n{}",  self.ip, self.port, repr(self.content))
            # self.process_json_content()

        elif self.header["type"] == 'image/jpeg':
            stream = io.BytesIO(data)  # convert received data into bytesIO object for PIL
            img = Image.open(stream)  # open object as JPEG
            # print("Received image. Length: {}, Size: {}".format(len(data), img.size))
            # img.save("./images/img_{}.png".format(strftime('%Y-%m-%d_%H-%M-%S')))  # save image
            self.num += 1  # received another image

        else:  # Binary or unknown content-type
            self.content = data
            print('Received {} response from [{}:{}}', self.header["type"], self.ip, self.port)
            # self.process_binary_content()

        self.reset()

    def reset(self):
        """ Reset all message variables, ready to receive another """
        self.proto = None
        self.header = None
        self.content = None

    def close(self):
        """ Disconnect """
        self.socket.close()
        print("Disconnected")
        print("Frames received:", self.num)
