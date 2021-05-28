from threading import Thread, Event
import subprocess
import inspect
import time
import json
import os


from utils import validate_input
from raspi import streamers
from raspi.pi_lib import CONFIG_PATH


def dmesg():
    """ Returns the last line of output from dmesg """
    # TODO: make this more robust to possible changes in future dmesg output formats
    sub = subprocess.Popen("dmesg | tail -1", shell=True, stdout=subprocess.PIPE)
    output = sub.stdout.read().decode('utf-8')
    return output


def detect_vcp(event):
    """
    Used to detect when a tty device is plugged in.
    To be called in a parallel thread while the user plugs the devices in.
    <event> is a threading event to communicate with the main thread
    config is a dictionary from outer scope, and should be changed in-place.
    """
    output = dmesg()
    while event.is_set():  # loop until event is un-set
        time.sleep(0.2)
        new_output = dmesg()
        if new_output != output:  # new entry to dmesg detected
            output = new_output
            index = new_output.find('tty')
            if index >= 0:  # found
                path = '/dev/' + new_output[index:-1]
                print(path, end='', flush=True)
                config['VCP'][event.current_key] = path
    # when event is unset from main thread, set event again to notify that it's done
    event.set()


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
ip = config.get('SERVER_IP')  # ip address of server
port = config.get('PORT')             # port to connect through
name = config.get('NAME')             # display name of this Client
selected = config.get('STREAMERS')    # Dictionary of streamer class to choose from
vcp = config.get('VCP')               # Dictionary mapping streamers to Virtual COM Ports that will receive data from the dongles
redis_port = config.get('DB_PORT')    # port for redis server
redis_pass = config.get('DB_PASS')    # password to redis server

# get all classes defined in 'streamers.py'
streamer_classes = []
for member in inspect.getmembers(streamers, inspect.isclass):
    if member[1].__module__.split('.')[-1] == 'streamers':
        streamer_classes.append(member)

# Check to see if all classes are included in the config options
all_in_config = True
if selected:
    for member in streamer_classes:
        if member[0] not in selected.keys():
            all_in_config = False
        if member[0] not in vcp.keys():
            all_in_config = False


# all settings present, not overwriting
if ip and port and name and selected and vcp and all_in_config and updating:
    print("\nAll config options are set. \nIf you wish to change anything you can edit '{}', \nor restart this script and choose to overwrite.".format(CONFIG_PATH))
    quit()

# file doesn't exist, or overwriting existing file
# TODO: Add regex input validation to all these options?
print("> Please provide the following information. These can be changed in {}\n".format(CONFIG_PATH))
if not ip:
    config['SERVER_IP'] = input("IP address of server: ")
if not port:
    config['SERVER_PORT'] = int(input("Server Port: "))
if not redis_port:
    config['DB_PORT'] = int(input("Database Port: "))
if not redis_pass:
    config['DB_PASS'] = input("Database Password: ")
if not name:
    config['NAME'] = input("Client name: ")
if not selected:
    config['STREAMERS'] = {}
    print("\n> Answer y/n to each of the following to select which Streamer classes are to be used.")
    for member in streamer_classes:
        name = member[0]
        ans = input("Use {}? ".format(name)).upper()
        # ans = 'y' if ans == '' else ans
        config['STREAMERS'][name] = ans
if not vcp:
    config['VCP'] = {}
    print("\n> Now we need to associate each streamer class with its corresponding serial port, if any.\n"
          "For each streamer classes listed below, please provide the full device path of its corresponding serial port.\n"
          "If you do not already know the device path, you may insert (or remove and re-insert) the device and we will attempt to detect it for you.\n"
          "If this succeeds, you should see the associated device path appear automatically a few seconds after inserted.\n"
          "If you do not see it appear, you may need to enter it manually in {} under the 'VCP' keyword.\n"
          "If the given streamer does not require a device path, type nothing.\n"
          "Press Enter to confirm each entry.\n".format(CONFIG_PATH))

    event = Event()  # threading event to regulate the parallel thread
    event.set()  # set to True
    event.current_key = ''  # string - current streamer key for the config dictionary
    Thread(target=detect_vcp, args=(event,), daemon=True).start()  # start looking for tty devices on different thread
    for member in streamer_classes:
        event.current_key = member[0]
        devpath = input("{}: ".format(member[0])).strip()  # wait for user to press enter
        if devpath:  # if user gave input
            config['VCP'][member[0]] = devpath
    event.clear()  # stop loop in other thread
    event.wait()  # wait until thread sets the event again to indicate that config has been updated

# set log file path.
# TODO: Option to configure this?
config['LOG_PATH'] = '../logs'

# After all config options set
with open(CONFIG_PATH, 'w+') as file:
    json.dump(config, file)  # dump config dictionary to the JSON config file
print("\n> Configuration complete. All options saved in {}".format(CONFIG_PATH))

