import io
import socket
import struct
from PIL import Image

host = ''           # allow any connection
port = 80        # TCP port 80

sock = socket.socket()     # socket object
sock.bind((host, port))    # bind to any ip with given port
sock.listen(0)             # wait for a connection

# Accept connection, make a file object from it
conn = sock.accept()[0].makefile('rb')

try:
    while True: 
        # Read length of image as a 32 bit unsigned int.
        image_len = struct.unpack('<L', conn.read(struct.calcsize('<L')))[0]
        if not image_len:  # end is zero
            break
        
        image_stream = io.BytesIO() # Stream to read image data
        image_stream.write(conn.read(image_len))  # read only length of image
        
        image_stream.seek(0)  # go back to beginning of stream
        image = Image.open(image_stream)
        
        try:  # check for image corruption
            image.verify()
            print("Image received")
        except:
            print("Image is broken or something")
finally:
    conn.close()  # close connection file
    sock.close()  # close socket
