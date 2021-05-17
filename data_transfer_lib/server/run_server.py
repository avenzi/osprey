import json

from server.server_lib import Server, CONFIG_PATH

# get configured settings if they already exist
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except Exception as e:
    print("no config file found")
    quit()

server = Server(debug=2)
server.run()

