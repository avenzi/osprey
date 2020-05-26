import io
import socket
import struct
import time
import picamera

host = "3.136.140.191"  # public ip of Ubuntu server
port = 8000             # TCP port 80

sock = socket.socket()      # socket object
sock.connect((host, port))  # bind to ip:port

# Make a file from connection
conn = client_socket.makefile('wb')
try:
    camera = picamera.PiCamera()  # picamera object
    camera.resolution = (640, 480)
    
    # Start a preview and let camera warm up for 2 seconds
    camera.start_preview()
    time.sleep(2)

    start = time.time()      # note start time
    stream = io.BytesIO()    # stream to hold image data
    for foo in camera.capture_continuous(stream, 'jpeg'):
        # Write the length of the capture to the stream and flush to send
        connection.write(struct.pack('<L', stream.tell()))
        connection.flush()
        
        # Go back to beginning of stream and write
        stream.seek(0)
        connection.write(stream.read())
        
        # Stop after 10 seconds
        if time.time() - start > 10:
            break
        
        # Reset stream for the next capture
        stream.seek(0)
        stream.truncate()
        
    # Write a length of zero to the stream to signal end
    connection.write(struct.pack('<L', 0))
    
finally:
    conn.close()
    sock.close()
