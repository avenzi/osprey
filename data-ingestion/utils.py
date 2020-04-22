import json
import os.path
import sys
from time import sleep

class Utils():
    def __init__(self):
        pass

    def get_config(self):
        with open(os.path.dirname(__file__) + "/../config.json") as config_file:
            return json.loads(config_file.read())
    
    def sleep(self):
        sleep(30000000)