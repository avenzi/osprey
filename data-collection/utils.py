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
    
    def clear_temporary_data(self):
        filelist = [ f for f in os.listdir("audio-segments") if f.endswith(".wav") ]
        for f in filelist:
            os.remove(os.path.join("audio-segments", f))
        
        filelist = [ f for f in os.listdir("mp3-segments") if f.endswith(".mp3") ]
        for f in filelist:
            os.remove(os.path.join("mp3-segments", f))
    
    def sleep(self):
        sleep(sys.maxsize)