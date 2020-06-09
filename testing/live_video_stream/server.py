import io
import os
import socket
import struct
from time import time, strftime, sleep
from PIL import Image

ip = '35.20.136.146'  # ip of raspberry pi
port = 8000           # TCP port 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # socket object
sock.connect((ip, port))
print("Socket connected")

conn = sock.makefile('rb')
print("Made file object from socket")
print(conn.read())

try:
    pass
finally:
    conn.close()  # close connection file
    sock.close()  # close socket
