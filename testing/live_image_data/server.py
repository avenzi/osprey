import io
import os
import socket
import struct
from time import time, strftime, sleep
from PIL import Image

host = ''           # allow any connection
port = 80        # TCP port 80

sock = socket.socket()     # socket object
sock.bind((host, port))    # bind to any ip with given port
sock.listen(0)             # wait for a connection

# Accept connection, make a file object from it
conn = sock.accept()[0].makefile('rb')
print("Connection Accepted")

caps_path = "./captures"  # directory of capturing sessions
if not os.path.exists(caps_path):
    os.makedirs(caps_path)

ims_path = "{}/{}".format(caps_path, strftime('%Y-%m-%d_%H-%M-%S'))  # dir named with data/time: YYYY-MM-DD_HH-MM-SS
if not os.path.exists(ims_path):
    os.makedirs(ims_path)
else:
    raise Exception("Image directory with same date and time already exists... how did you manage that?")


try:
    num = 0  # for counting images captured
    while True: 

        # Read length of image as a 32 bit unsigned int.
        image_len = struct.unpack('<L', conn.read(struct.calcsize('<L')))[0]
        if not image_len:  # end is zero
            break
        
        image_stream = io.BytesIO() # Stream to read image data
        image_stream.write(conn.read(image_len))  # read only length of image
        
        image_stream.seek(0)  # go back to beginning of stream
        image = Image.open(image_stream)
        
        num += 1
        try:  # check for image corruption
            image.verify()
            print("Image received: ", num)
        except:
            print("Image could not be verified: ", num)

        image = Image.open(image_stream)
        try:
            path = "{}/image_{}.png".format(ims_path, num)
            image.save(path)
            #data = list(image.getdata())
            #print(data[:20])
        except Exception as e:
            print("Failed: ", e)
finally:
    conn.close()  # close connection file
    sock.close()  # close socket
