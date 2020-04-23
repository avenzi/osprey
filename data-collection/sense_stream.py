from sense_hat import SenseHat

import io
import time
import threading
import datetime
import requests
from queue import Queue

class SenseStream(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.server = args[0]

    def run(self):
        if self.validate_setup():
            self.stream()
    
    def validate_setup(self):
        try:
            self.sense = SenseHat()
            print("Sense HAT: detected")
            return True
        except Exception as e:
            return False

    def stream(self):
        # Send data forever
        while True:
            # Wait 1 second between updates
            time.sleep(1)
            
            try:
                temp = self.sense.get_temperature()
                press = self.sense.get_pressure()
                humid = self.sense.get_humidity()

                # Convert temperature to F
                temp = ((temp/5) * 9) + 32

                # Create data object with temperature, pressure, and humidity data
                sense_data = {"Temp": temp, "Press": press, "Humid": humid}
                
                requests.post(self.server,
                    data = sense_data,
                )
            except Exception as e:
                print("Exception caught:", e)
            
