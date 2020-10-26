import json
import inspect

from .pi_lib import Client, CONFIG_PATH
from . import streamers

# get configured settings
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except FileNotFoundError:
    config = {}
except Exception as e:
    print("JSON in config file was probably corrupt or empty.\nReinitializing file: {}\n Error: {}".format(CONFIG_PATH, e))
    config = {}

ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
port = config.get('PORT')             # port to connect through
name = config.get('NAME')             # display name of this Client
handlers = config.get('HANDLERS')     # Dictionary of handler class to choose from

# get all classes in 'streamers'
class_names = [member[0] for member in inspect.getmembers(streamers, inspect.isclass) if member[1].__module__.split('.')[-1] == 'streamers']

# Check to see if all classes have a config option
all_in_config = True
if handlers:
    for class_name in class_names:
        if class_name not in handlers.keys():
            all_in_config = False

# TODO: Add input validation to all these options?
if not(ip and port and name and handlers and all_in_config):
    print("\n> Configuration options are not yet set. \
          \n  Please provide the requested information. \
          \n  These can be changed in {}\n".format(CONFIG_PATH))
    if not ip:
        config['SERVER_IP_ADDRESS'] = input("IP address of server: ")
    if not port:
        config['PORT'] = int(input("Port: "))
    if not name:
        config['NAME'] = input("Client name: ")
    if not handlers:
        config['HANDLERS'] = {}
        print("\n> Answer Y/N to each of the following (or press Enter for Y)\n  to select which Streamer classes\n  are to be used for this client.")
        for name in class_names:
            ans = input("Use {}? ".format(name)).upper()
            ans = 'Y' if ans == '' else ans
            config['HANDLERS'][name] = ans

    with open(CONFIG_PATH, 'w') as file:
        json.dump(config, file)
    print("\n> Configuration complete. \n  All options saved in {}".format(CONFIG_PATH))
    ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
    port = config.get('PORT')             # port to connect through
    name = config.get('NAME')             # display name of this Client

client = Client(ip, port, name=name)
client.run()




