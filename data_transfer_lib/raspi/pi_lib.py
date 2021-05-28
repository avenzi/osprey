from threading import Condition
from io import BytesIO
import subprocess
import inspect
import os

from lib import Client

CONFIG_PATH = '../config/raspi_config.json'


def configure_port(dev_path):
    """
    Used for data collection devices which rely on the Pi's internal timer to time-stamp data.
    Sets the internal buffer for the given VCP port to 1ms-latency in order to avoid data chunking.
    This setting gets reset when the device is disconnected or the Pi is power cycled,
        so it needs to be run each time the client begins streaming
    """
    device = dev_path[dev_path.index('tty'):]
    filepath = "/sys/bus/usb-serial/devices/{}/latency_timer".format(device)
    if os.path.exists(filepath):
        subprocess.Popen("echo 1 | sudo tee {}".format(filepath), shell=True, stdout=subprocess.PIPE)
        return True
    else:
        print("Could not configure serial device - path doesn't exist")
        return False


class RaspiClient(Client):
    """ Extends the Client HostNode to run Streamers on a Raspberry Pi """
    def _run(self):
        """
        Called by self.run() on a new thread.
        Creates one instance of each handler type from collection_lib
            For each handler class, listens for new connections then starts them on their own thread.
        """
        self.log("Name: {}".format(self.name))
        #self.log("Device IP: {}".format(get('http://ipinfo.io/ip').text.strip()))  # show this machine's public ip
        self.log("Server IP: {}:{}".format(self.config['SERVER_IP'], self.config['SERVER_PORT']))
        self.log("Database IP: {}:{}".format(self.config['SERVER_IP'], self.config['DB_PORT']))

        # get selected handler classes
        from . import streamers
        members = inspect.getmembers(streamers, inspect.isclass)  # all classes [(name, class), ]
        for member in members:
            if member[1].__module__.split('.')[-1] == 'streamers':  # imported from the streamers.py file
                config = self.config['STREAMERS'].get(member[0])  # configuration of whether this class is to be used or not
                if config and config.upper() == 'Y':  # this class is in the config file and set to be used
                    self.run_worker(member[1])  # create a new worker and on a parallel process
                else:  # not in the config file or not set to be used
                    self.debug("Streamer class {} is not being used. Set it's keyword to 'Y' in {} to use".format(member[0], CONFIG_PATH))


class PicamOutput():
    """ Data Buffer class to collect data from a Picam. """
    def __init__(self):
        self.buffer = BytesIO()
        self.ready = Condition()  # lock for reading/writing frames

    def write(self, data):
        """ Write data to the buffer, adding the new frame when necessary """
        with self.ready:
            self.buffer.write(data)
            self.ready.notify_all()

    def read(self):
        """ Blocking operation to read the newest frame """
        with self.ready:
            self.ready.wait()  # wait for access to buffer
            data = self.buffer.getvalue()  # get all frames in buffer
            self.buffer.seek(0)  # move to beginning
            self.buffer.truncate()  # erase buffer
            return data


