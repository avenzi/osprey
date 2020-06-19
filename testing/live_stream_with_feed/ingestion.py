import json
from ingestion_lib import Server

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']

server = Server(port, name="Server", debug=True)
server.serve()

