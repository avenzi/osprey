from threading import Thread, Event
import subprocess
import time


def dmesg():
    """ Returns the last line of output from dmesg """
    # TODO: make this more robust to possible changes in future dmesg output formats?
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
                print('/dev/{}'.format(new_output[index:-1]))


print("\n> This tool will help identify the path to devices plugged into this Raspberry Pi.\n"
      "To identify the path of a device, insert it into the desired port. \n"
      "The path of that port should appear below.\n"
      "Press Enter when finished.\n")

event = Event()  # threading event to regulate the parallel thread
event.set()  # set to True
Thread(target=detect_vcp, args=(event,), daemon=False).start()  # start looking for tty devices on different thread
input("")  # wait for user to press enter
event.clear()  # stop loop in other thread