import subprocess
import time
from threading import Thread

CONFIG_PATH = 'config_path'

print("\nPlease insert (or remove and re-insert) each OpenBCI dongle that will be used by this device.\n"
      "You should see the associated device path appear below for each dongle after inserted. When done, press Enter.\n"
      "(If you do not see their device path(s) appear below, you may have to enter them manually afterward in {}):".format(CONFIG_PATH))

MOVE_ON = False

def detect_vcp():
    ports = []  # all device paths found
    print("Device Paths Detected: ")
    while not MOVE_ON:
        time.sleep(0.5)
        sub = subprocess.Popen("dmesg | tail -1", shell=True, stdout=subprocess.PIPE)
        output = sub.stdout.read().decode('utf-8')
        index = output.find('ttyUSB')
        if index >= 0:  # found
            path = '/dev/'+output[index:-1]
            if path not in ports:
                print('> ', path)
                ports.append(path)
Thread(target=detect_vcp).start()
input('')
MOVE_ON = True
print("DONE")



