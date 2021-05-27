import json
import os
from requests import get

from utils import validate_input
from server.analysis_lib import CONFIG_PATH

updating = False  # flag if updating existing config settings

# check for existing config file
if os.path.isfile(CONFIG_PATH):
    ans = validate_input("Found an existing config file.\nOverwrite? (y/n): ", ['y', 'n'])
    if ans == 'y':
        print("All config setting will be overwritten.")
        config = {}
    else:
        updating = True
        with open(CONFIG_PATH) as file:
            config = json.load(file)
else:
    config = {}


# get all settings in the file, which will be None if they don't exist
port = config.get('SERVER_PORT')
name = config.get('NAME')
redis_port = config.get('REDIS_PORT') # port for redis server
redis_pass = config.get('REDIS_PASS') # password to redis server

# all settings present, not overwriting
if port and name and updating:
    print("\nAll config options are set. \nIf you wish to change anything you can edit '{}', \nor restart this script and choose to overwrite.".format(CONFIG_PATH))
    quit()

# file doesn't exist, or overwriting existing file
# TODO: Add regex input validation to all these options?
print("> Please provide the following information. These can be changed in {}\n".format(CONFIG_PATH))
if not name:
    config['NAME'] = input("Server display name: ")
if not port:
    config['SERVER_PORT'] = int(input("Server Port: "))
if not redis_port:
    config['REDIS_PORT'] = int(input("Redis Database Port: "))
if not redis_pass:
    config['REDIS_PASS'] = input("Redis Database Password: ")

config['SERVER_IP'] = get('http://ipinfo.io/ip').text.strip()

# set log file path and data file path.
# TODO: Option to configure this
config['LOG_PATH'] = '../logs'
config['DATA_PATH'] = '../data'

# After all config options set
with open(CONFIG_PATH, 'w+') as file:
    json.dump(config, file)  # dump config dictionary to the JSON config file
print("\n> Configuration complete. All options saved in {}".format(CONFIG_PATH))

