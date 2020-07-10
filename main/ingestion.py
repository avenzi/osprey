import json
from lib import Server
from ingestion_lib import Handler

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']
name = config['NAME']

server = Server(Handler, port, name=name, debug=2)
server.run()

