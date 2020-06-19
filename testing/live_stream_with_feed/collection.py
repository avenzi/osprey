import json
from collection_lib import VideoClient

# get configured settings
with open('config.json') as file:
    config = json.load(file)
    
ip = config['SERVER_IP_ADDRESS']
port = config['PORT']

laptop_ip = '35.11.244.179'  # public ip of Aven's laptop

streamer = VideoClient(laptop_ip, port, name="Video Client")
streamer.serve()


