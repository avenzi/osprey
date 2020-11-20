import json

from .pi_lib import Client, CONFIG_PATH

# get configured settings if they already exist
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except Exception as e:
    # TODO: Send an error message to the log
    quit()

ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
port = config.get('PORT')             # port to connect through
name = config.get('NAME')             # display name of this Client

client = Client(ip, port, name=name)  # create client object with config settings
client.run()  # run the client




