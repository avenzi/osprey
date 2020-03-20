from sense_hat import SenseHat
import time
import sys
import requests

#function to stream SENSE Hat data to a server
#prints error data to a specified log file
def stream(server, log=sys.stdout):
    sense = SenseHat()

    # fails out if connection broken
    while True:
        # Wait 1 second between updates
        time.sleep(1)
        
        
        try:
            temp = sense.get_temperature()
            press = sense.get_pressure()
            humid = sense.get_humidity()


            # convert temperature to F
            temp = ((temp/5) * 9) + 32

            # Create data object with temperature, pressure, and humidity data
            sense_data = {"Temp": temp, "Press": press, "Humid": humid}
            
            # Debugging
            #print(temp, file = log)
          
            requests.post(server,
                    data = sense_data,
            )
            
        
        except Exception as e:
            # print to log file
            print("Exception caught:", e, file=log)
            
