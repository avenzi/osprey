import picamera
import struct
from time import strftime, sleep
from requests import get

import io
import logging
import socket
from threading import Condition
from http import server

from ingestion_lib import encode_json, decode_json


class Streamer():
    """ Connects to the remote server and streams the data """
    
    def __init__(self, ip, port, resolution='640x480', framerate=24, debug=False):
        self.camera = None
        self.resolution = resolution
        self.framerate = framerate
        
        self.ip = ip  # ip of remote server
        #self.myip = get('http://ipinfo.io/ip').text.strip()  # public ip of Raspi
        self.port = port
        self.socket = None    # socket object to send data to
        self.output = None    # file-like object to write and read images from

        self.number_sent = 0  # number of images sent
        
        self.debug = debug
        
    def stream(self):
        """ Connect to server and continually stream data from the output buffer ot the TCP stream """
        self.connect()  # connect socket to server
        self.start()    # start recording
        print("Streaming...")
        
        try:
            while True:
                self.write()  # write individual frames
        except Exception:
            print('> Ingestion Stream Disconnected ({}:{})'.format(self.ip, self.port))
        finally:
            self.stop()  # stop recording
            self.disconnect()  # disconnect socket
        
    def start(self):
        self.camera = picamera.PiCamera(resolution=self.resolution, framerate=self.framerate)
        self.output = StreamOutput()  # file-like output object for the picamera to write to
        self.camera.start_recording(self.output, format='mjpeg')
        print("> Started Recording:", strftime('%Y/%m/%d %H:%M:%S'))
        sleep(2)
    
    def stop(self):
        self.camera.stop_recording()
        print("> Stopped Recording:", strftime('%Y/%m/%d %H:%M:%S'))
        
    def connect(self):
        """ Create and connect to socket via given address. """
        try:   # create socket object
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
            print("> Socket Created...")
        except Exception as e:
            raise Exception("Failed to create socket: {}".format(e))

        try:  # connect socket to given address
            print("> Attempting to connect to {}:{}".format(self.ip, self.port))
            self.socket.connect((self.ip, self.port))
            print("> Socket Connected.")
        except Exception as e:
            raise Exception("Failed to connect: {}".format(e))

    def write(self):
        """ Write an image and accompanying data to the TCP stream once """
        with self.output.condition:
            self.output.condition.wait()
            frame = self.output.frame  # get next frame from picam
            
        self.number_sent += 1
        header = {'length': len(frame), 'number': self.number_sent}
        header_bytes = encode_json(header, 'utf-8')  # encode header into bytes
        proto_bytes = struct.pack('>H', len(header_bytes))  # proto-header, big-endian unsigned short
        
        self.socket.sendall(proto_bytes)  # send proto (length of header)
        self.socket.sendall(header_bytes)
        self.socket.sendall(frame)
        
        self.log('Proto:', proto_bytes, len(header_bytes))
        self.log('Header:', header_bytes)
        self.log('Frame:', frame)
    
    def disconnect(self):
        """ Disconnect socket from server """
        self.socket.close()
        print("> Connection Closed.")
    
    def log(self, *args):
        """ Prints out message is debug is True """
        if self.debug:
            print(*args)
        
        
class StreamOutput(object):
    """
    Used by Picam's start_recording() method.
    Writes frames to a buffer to be sent to the client
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()  # notify all clients that it's available
            self.buffer.seek(0)
        return self.buffer.write(buf)

