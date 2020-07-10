import json
from lib import Server
from ingestion_lib import Handler

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']

server = Server(Handler, port, name="Data Hub Server", debug=2)
server.run()

