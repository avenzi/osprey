import json
from lib import StreamServer

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']

server = StreamServer(port)

