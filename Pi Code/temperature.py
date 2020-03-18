from sense_hat import SenseHat
import time
import io
import struct
import socket
import requests
from http import server

#function to stream temperature data to a server
def stream(server, log):
    sense = SenseHat()

    # fails out if connection broken
    while True:
        try:
            temp = sense.get_temperature()
            press = sense.get_pressure()
            humid = sense.get_humidity()


            # convert to F
            temp = ((temp/5) * 9) + 32

            # Create data object
            sense_data = {"Temp": temp, "Press": press, "Humid": humid}
            
            print(temp, file = log)
          
            requests.post(server,
                    data = sense_data,
            )

            # Wait 1 second between updates
            time.sleep(1)
        
        except Exception as e:
            # log file
            print("Exception caught:", e, file = log)
            

        #finally:
            #connection.close()
            
