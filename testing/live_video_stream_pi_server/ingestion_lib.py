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

        self.number_received = 0       # number of images received
        self.number_sent = 0           # number of images sent from the pi (sent in header)

    def stream(self):
        """
        Create and connect to socket,
        then read from the TCP continually,
        disconnecting on error.
        """
        self.connect()
        try:
            while True:
                self.read()
        finally:
            self.close()
            print("Frames Received: {}/{}".format(self.number_received, self.number_sent))

    def connect(self):
        """ Create and connect to socket via given address. """
        try:   # create socket object
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
            print("Socket Created...")
        except Exception as e:
            raise Exception("Failed to create socket: \n{}".format(e))

        try:  # connect socket to given address
            self.socket.connect((self.ip, self.port))
            print("Socket Connected...")
        except Exception as e:
            raise Exception("Failed to connect to socket on {}:{} \n{}".format(self.ip, self.port, e))

        # Send custom request method CLIENTSTREAM to let the server know that this is the ingestion client.
        # The rest of the data sent is to just to fulfill the request syntax.
        # The two newlines add a blank line to the request, denoting that its a complete packet
        self.socket.sendall(b'CLIENTSTREAM /index.html HTTP/1.1 \r\n\n')
        print('Sent Stream Request...')

    def read(self):
        """ read from the TCP stream one time """
        try:
            data = self.socket.recv(4096)  # receive data from pi
        except BlockingIOError:  # Temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:  # if received data
                self.in_buffer += data  # append to in-buffer
            else:
                raise Exception('Stream Disconnected')

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
        # print("Got proto:", self.proto)

    def parse_header(self):
        """ Parse the header from the start of the buffer, stores in self.header """
        header_len = self.proto

        # Complete header not yet received
        if len(self.in_buffer) < self.proto:
            return

        self.header = decode_json(self.in_buffer[:header_len], 'utf-8')  # parse header
        self.in_buffer = self.in_buffer[header_len:]  # move down the buffer
        # print("Got header:", self.header)

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
        # print("Received image. Length: {}, Size: {}".format(len(data), img.size))
        # img.save("./images/img_{}.png".format(strftime('%Y-%m-%d_%H-%M-%S')))  # save image

        self.number_received += 1  # received another image
        self.number_sent = self.header['number']  # update number sent from pi
        self.reset()      # reset class attributes to prepare for another image

    def reset(self):
        """ Reset all message variables, ready to receive another """
        self.proto = None
        self.header = None
        self.content = None

    def close(self):
        """ Disconnect """
        self.socket.close()
        print("Disconnected")
