import json
from lib.server_lib import Server

# get configured settings
with open('config.json') as file:
    config = json.load(file)

port = config.get('PORT')
name = config.get('NAME')

if not(port and name):
    print("> Configuration options are not yet set. \
          \n  Please provide the requested information. \
          \n  These can be changed in ./config.json\n")
    if not port:
        config['PORT'] = int(input("Port: "))
    if not name:
        config['NAME'] = input("Server name: ")

    with open('config.json', 'w') as file:
        json.dump(config, file)
    print("\n> Configuration complete. \n  All options saved in config.json.")
    port = config.get('PORT')             # port to connect through
    name = config.get('NAME')             # display name of this Client

server = Server(port, name=name)
server.run()

