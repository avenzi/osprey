import time
from datetime import datetime
import video
import temperature
import socket



# IP and socket to connect to
server = "http://51.161.8.254:5568"

log = open("/home/pi/Desktop/Streaming/Logs/" + str(datetime.now()), "w+")



# Wait for active internet connection to support headless operation
#while True:
#    try:
#        socket.gethostbyname("google.com")
#        break
#
#    except:
#        time.sleep(1)

# continuously attempt to start connection
#while True:
for i in range(2):
    try:
        # Write to log file
        #print("Attemping Video Connection")
        #video.stream(server)
        
        
        # Each pi will have all code, but only call the
        # functions relating to necessary streams
        temperature.stream(server, log)
        
    except Exception as e:
        # Write to log file
        print("Exception caught: ", e, file = log)
        time.sleep(.5) # reduced from 2 to minimize connection lag
        
log.close()
