import json
from lib import Client
from collection_lib import VideoClientHandler

# get configured settings
with open('config.json') as file:
    config = json.load(file)
    
ip = config['SERVER_IP_ADDRESS']
port = config['PORT']
name = config['NAME']

client = Client(VideoClientHandler, ip, port, name=name, debug=2)
client.run()


