from sense_hat import SenseHat
import time
import io
import struct
import socket
import requests
from http import server

#function to stream temperature data to a server
def stream(server, log):
    # Identify to ingestion as temperature stream
    #connection.write(struct.pack('<H', 1))
    #client_socket.send(struct.pack('<H', 1))
    
    time.sleep(1)
    
    sense = SenseHat()

    # fails out if connection broken
    #for i in range(3):
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
            #client_socket.close()
            

        #finally:
            #connection.close()
            
