from collection_lib import Streamer

IP = '35.11.244.179'
PORT = 5000  # port on which to host the stream

streamer = Streamer(IP, PORT)
streamer.stream()