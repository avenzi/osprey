from time import time, strftime, sleep
from ingestion_lib import ServerHandler

ip = '35.20.136.146'  # ip of raspberry pi
port = 8000           # TCP port 8000

handler = ServerHandler(ip, port)
handler.connect()

try:
    while True:
        handler.read()  # read from TCP stream
finally:
    handler.close()  # close connection
