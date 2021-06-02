import json
from lib.server.analysis_lib import AnalyzerClient, CONFIG_PATH

# get configured settings if they already exist
try:
    with open(CONFIG_PATH) as file:
        config = json.load(file)
except Exception as e:
    # TODO: Send an error message to the log
    print('No config file found. Please run the appropriate setup script.')
    quit()


client = AnalyzerClient(config, debug=2)
client.run()







