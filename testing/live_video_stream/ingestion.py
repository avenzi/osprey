from time import time, strftime, sleep
from requests import get
from ingestion_lib import StreamHandler

port = 5000           # TCP port

print("IP:", get('http://ipinfo.io/ip').text.strip())
handler = StreamHandler(port)
handler.stream()
