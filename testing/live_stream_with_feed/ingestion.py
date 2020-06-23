import json
from lib import Server
from ingestion_lib import ServerHandler

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']

server = Server(ServerHandler, port, name="Server", debug=True)
server.run()

