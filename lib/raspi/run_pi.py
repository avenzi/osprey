import json
from lib.raspi.pi_lib import RaspiClient, CONFIG_PATH

# get configured settings if they already exist
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except Exception as e:
    print('No config file found. Please run the appropriate setup script first.')
    quit()


client = RaspiClient(config, debug=2)
client.run()




