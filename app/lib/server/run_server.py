import json
import os
from .server_lib import Server, CONFIG_PATH

# get configured settings
try:
    with open(CONFIG_PATH, 'r') as file:
        config = json.load(file)
except FileNotFoundError:
    config = {}
except Exception as e:
    print("JSON in config file was probably corrupt or empty.\nReinitializing file: {}\n Error: {}".format(CONFIG_PATH, e))
    config = {}

port = config.get('PORT')
name = config.get('NAME')

if not(port and name):
    print("> Configuration options are not yet set. \
          \n  Please provide the requested information. \
          \n  These can be changed in {}\n".format(CONFIG_PATH))
    if not port:
        config['PORT'] = int(input("Port: "))
    if not name:
        config['NAME'] = input("Server name: ")

    with open(CONFIG_PATH, 'w') as file:
        json.dump(config, file)
    print("\n> Configuration complete. \n  All options saved in {}".format(CONFIG_PATH))

server = Server(debug=2)
server.run()

