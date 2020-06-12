import json
from ingestion_lib import StreamHandler

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config['PORT']

handler = StreamHandler(port)
handler.stream()
