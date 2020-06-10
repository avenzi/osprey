from time import time, strftime, sleep
from ingestion_lib import ServerHandler

ip = '35.20.136.146'  # ip of raspberry pi
port = 8000           # TCP port 8000

handler = ServerHandler(ip, port)
handler.connect()

i = 0
while i < 10:
    handler.read()  # read from TCP stream
    i += 1

try:
    pass
finally:
    handler.close()  # close connection
