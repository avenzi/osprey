import socket
from requests import get
from lib import StreamBase


class StreamServer(StreamBase):
    def __init__(self, port, debug=False):
        super().__init__('', port, debug)  # accept any ip on this port

    def setup(self):
        """ Create socket and bind to local address then wait for connection from client """
        self.log("IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        self.log("Socket Created")

        try:  # Bind socket to ip and port
            #self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow socket to reuse address
            sock.bind((self.ip, self.port))  # accept any ip on this port
            if self.ip == '':
                self.log("Socket Bound to *:{}".format(self.port))
            else:
                self.log("Socket Bound to {}:{}".format(self.ip, self.port))
        except Exception as e:
            self.error("Failed to bind socket to {}:{}".format(self.ip, self.port), e)

        try:  # Listen for connection
            self.log("Listening for Connection...")
            sock.listen()
        except Exception as e:
            self.error("Error while listening on {}:{}".format(self.ip, self.port), e)

        try:  # Accept connection. Accept() returns a new socket object that can send and receive data.
            self.socket, (self.pi_ip, self.pi_port) = sock.accept()
            self.log("Accepted Connection From {}:{}".format(self.pi_ip, self.pi_port))
        except Exception as e:
            self.error("Failed to accept connection from {}:{}".format(self.pi_ip, self.pi_port), e)

        # if self.timeout is not None:  # is this needed?
        #    self.socket.settimeout(self.timeout)

    def stream(self):
        """ Read from the TCP continually, disconnecting on error. """
        msg = False  # flag for displaying the streaming notification
        while not self.exit:  # run until exit status is set
            self.handle()  # parse and handle all incoming requests
            if self.frames_received == 1 and not msg:  # just for displaying the Streaming message
                msg = True
                self.log("Streaming...", level='status')

    def finish(self):
        """ Executes on termination """
        self.log("Frames Received: {}/{}".format(self.frames_received, self.frames_sent))

    def INGEST(self):
        """ Handle image data received from Pi """
        frame = self.content
        self.frames_received += 1
        self.frames_sent = self.header['frames-sent']

    def GET(self):
        """ Handle request from web browser """