from threading import Thread, Event
import subprocess
import inspect
import time
import json
import os


from ..lib import validate_input
from .pi_lib import CONFIG_PATH
from . import streamers


def detect_vcp(event):
    """
    Used to detect when a tty device is plugged in.
    To be called in a parallel thread while the user plugs the devices in.
    <event> is a threading event to communicate with the main thread
    config is a dictionary from outer scope, and should be changed in-place.
    """
    ports = []  # all device paths found
    print("Device Paths Detected: ")
    while event.is_set():  # loop until event is un-set
        time.sleep(0.5)
        sub = subprocess.Popen("dmesg | tail -1", shell=True, stdout=subprocess.PIPE)
        output = sub.stdout.read().decode('utf-8')
        index = output.find('ttyUSB')
        if index >= 0:  # found
            path = '/dev/' + output[index:-1]
            if path not in ports:
                print('> ', path)
                ports.append(path)
    config['VCP'] = ports
    event.set()  # set event, notifying that the config dict has been updated


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
ip = config.get('SERVER_IP_ADDRESS')  # ip address of server
port = config.get('PORT')             # port to connect through
name = config.get('NAME')             # display name of this Client
handlers = config.get('HANDLERS')     # Dictionary of handler class to choose from
vcp = config.get('VCP')               # List if Virtual COM Ports that will receive data from the dongles

# get all classes defined in 'streamers.py'
class_names = [member[0] for member in inspect.getmembers(streamers, inspect.isclass) if member[1].__module__.split('.')[-1] == 'streamers']

# Check to see if all classes have a config option
all_in_config = True
if handlers:
    for class_name in class_names:
        if class_name not in handlers.keys():
            all_in_config = False


# all settings present, not overwriting
if ip and port and name and handlers and vcp and all_in_config and updating:
    print("\nAll config options are set. \nIf you wish to change anything you can edit '{}', \nor restart this script and choose to overwrite.".format(CONFIG_PATH))
    quit()

# file doesn't exist, or overwriting existing file
# TODO: Add regex input validation to all these options?
print("\n> Please provide the following information. These can be changed in {}\n".format(CONFIG_PATH))
if not ip:
    config['SERVER_IP_ADDRESS'] = input("IP address of server: ")
if not port:
    config['PORT'] = int(input("Port: "))
if not name:
    config['NAME'] = input("Client name: ")
if not handlers:
    config['HANDLERS'] = {}
    print("\n> Answer y/n to each of the following to select which Streamer classes are to be used.")
    for name in class_names:
        ans = input("Use {}? ".format(name)).upper()
        # ans = 'y' if ans == '' else ans
        config['HANDLERS'][name] = ans
if not vcp:
    print("\nPlease insert (or remove and re-insert) each OpenBCI dongle that will be used by this device.\n"
          "You should see the associated device path appear below for each dongle after inserted. When done, press Enter.\n"
          "(If you do not see their device path(s) appear below, you may have to enter them manually afterward in {}):".format(CONFIG_PATH))
    event = Event()  # threading event to regulate the parallel thread
    event.set()  # set to True
    Thread(target=detect_vcp, args=(event,)).start()  # start looking for tty devices on different thread
    input('')  # wait for user to press enter
    event.clear()  # stop loop in other thread
    event.wait()  # wait until thread sets the event again to indicate that config has been updated

# After all config options set
with open(CONFIG_PATH, 'w+') as file:
    json.dump(config, file)  # dump config dictionary to the JSON config file
print("> Configuration complete. All options saved in {}".format(CONFIG_PATH))

