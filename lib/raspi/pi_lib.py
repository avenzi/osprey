from threading import Condition
from io import BytesIO
import subprocess
import os


def configure_port(dev_path):
    """
    Used for data collection devices which rely on the Pi's internal timer to time-stamp data.
    Sets the internal buffer for the given VCP port to 1ms-latency in order to avoid data chunking.
    This setting gets reset when the device is disconnected or the Pi is power cycled,
        so it needs to be run each time the client begins streaming
    """
    # TODO: On one of the Raspberry Pis, the permissions on the dir that this symlink points to
    #  default to 660, so it can't be accessed. Need to figure out how to automatically check for
    #  this issue and change the permissions to something like 755 so it can be accessed.
    device = dev_path[dev_path.index('tty'):]
    filepath = "/sys/bus/usb-serial/devices/{}/latency_timer".format(device)
    if os.path.exists(filepath):
        subprocess.Popen("echo 1 | sudo tee {}".format(filepath), shell=True, stdout=subprocess.PIPE)
        return True
    else:
        print("Could not configure serial device - path doesn't exist")
        return False


class BytesOutput:
    """ Data Buffer class to collect data from a Picam. """
    def __init__(self):
        self.buffer = BytesIO()
        self.ready = Condition()  # lock for reading/writing frames

    def write(self, data):
        """ Write data to the buffer, adding the new frame when necessary """
        with self.ready:
            count = self.buffer.write(data)
            self.ready.notify_all()  # notify waiting read() calls
            # TODO: Does notify_all cause exclusive access violation? Change to notify()?
            return count

    def read(self):
        """ Blocking operation to read the newest frame """
        with self.ready:
            self.ready.wait()  # wait for access to buffer
            data = self.buffer.getvalue()  # get all frames in buffer
            self.buffer.seek(0)  # move to beginning
            self.buffer.truncate()  # erase buffer
            return data


class BytesOutput2(BytesIO):
    """ Data Buffer class to collect data from a Picam. """
    def __init__(self):
        super().__init__()
        self.ready = Condition()  # lock for reading/writing frames

    def write(self, data):
        """ Write data to the buffer, adding the new frame when necessary """
        with self.ready:
            count = super().write(data)
            self.ready.notify_all()  # notify waiting read() calls
            # TODO: Does notify_all cause exclusive access violation? Change to notify()?
            return count

    def read(self, size=-1):
        """ Blocking operation to read the newest frame """
        with self.ready:
            self.ready.wait()  # wait for access to buffer
            if not super().getvalue():  # no data
                print('no data in buff')
                return super().getvalue()
            self.seek(0)  # move to beginning
            data = super().read(size)  # read contents
            self.seek(0)  # move to beginning
            self.truncate()  # erase buffer
            return data


