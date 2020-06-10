import picamera
from requests import get

from collection_lib import StreamingOuput, StreamingServer, StreamingHandler
from ingestion_lib import encode_json, decode_json

PORT = 8000  # port on which to host the stream

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    print("Started Recording")

    try:
        address = ('', PORT)
        server = StreamingServer(address, StreamingHandler)
        ip = get('http://ipinfo.io/ip').text.replace('\n','')
        print("Starting Server:  {}:{}".format(ip, PORT))
        server.serve_forever()
    finally:
        camera.stop_recording()  # stop recording on error or termination
        print("Stopped Recording.")
