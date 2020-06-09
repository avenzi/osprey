import io
import os
import socket
import struct
import binascii
from time import time, strftime, sleep
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

ip = '35.20.136.146'  # ip of raspberry pi
port = 8000           # TCP port 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # socket object
sock.connect((ip, port))
print("Socket connected")

i = 0
while i < 10:

    #length = sock.recv(64)  # look for header?
    #print("Length:", length)
    
    data = sock.recv(100000) # replace 100000 with length specified in header
    print("Measured Length:", len(data))
    
    stream = io.BytesIO(data)  # convert received data into bytes object
    img = Image.open(stream)   # open bytes object as JPEG
    #print("Image Size:", img.size)
    
    img.save("./images/test_{}.png".format(i))  # save image
    print("saved image {}".format(i))
    #draw = ImageDraw.Draw(img)
    
    #font = ImageFont.truetype("arial.ttf",14)
    #draw.text((0, 220),"This is a test11",(255,255,0),font=font)
    #draw = ImageDraw.Draw(img)
    i += 1

#conn = sock.makefile('rb')
#print("Made file object from socket")



try:
    pass
finally:
    #conn.close()  # close connection file
    sock.close()  # close socket
