import json

from .pi_lib import Client, CONFIG_PATH

# get configured settings if they already exist
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except Exception as e:
    # TODO: Send an error message to the log
    quit()


client = Client(debug=2)  # create client
client.run()  # run the client




