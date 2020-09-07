import json
import inspect
from lib.pi_lib import Client
import streamers

# get configured settings
try:
    with open('config.json') as file:
        config = json.load(file)
except FileNotFoundError:
    config = {}
    
ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
port = config.get('PORT')             # port to connect through
name = config.get('NAME')             # display name of this Client
handlers = config.get('HANDLERS')     # Dictionary of handler class to choose from

# TODO: Add input validation to all these options
if not(ip and port and name and handlers):
    print("> Configuration options are not yet set. \
          \n  Please provide the requested information. \
          \n  These can be changed in ./config.json\n")
    if not ip:
        config['SERVER_IP_ADDRESS'] = input("IP address of server: ")
    if not port:
        config['PORT'] = int(input("Port: "))
    if not name:
        config['NAME'] = input("Client name: ")
    if not handlers:
        config['HANDLERS'] = {}
        # get all classes in collection_lib
        class_names = [member[0] for member in inspect.getmembers(streamers, inspect.isclass) if member[1].__module__ == 'collection_lib']
        print("\n> Answer Y/N to each of the following\n  to select which Handler classes\n  are to be used for this client.")
        for name in class_names:
            config['HANDLERS'][name] = input("Use {}? ".format(name)).upper()

    with open('config.json', 'w') as file:
        json.dump(config, file)
    print("\n> Configuration complete. \n  All options saved in config.json.")
    ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
    port = config.get('PORT')             # port to connect through
    name = config.get('NAME')             # display name of this Client

client = Client(ip, port, name=name)
client.run()




