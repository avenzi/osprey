import sys
import time

# Checking for updated data values every two seconds
while True:
    for line in sys.stdin:

        print("Updating values...")

        dataString = line.split('/')
        temperatureData_roomTemperature = dataString[0]
        temperatureData_skinTemperatureSub1 = dataString[1]
        temperatureData_skinTemperatureSub2 = dataString[2]
        temperatureData_status = dataString[3]
        temperatureData_date = dataString[4]
        audioData_decibels = dataString[5]
        audioData_status = dataString[6]
        audioData_date = dataString[7]
        eventLogData_temperatureStatus = dataString[8]
        eventLogData_audioStatus = dataString[9]

    time.sleep(2)    