#!/bin/bash

printf "Please specify which Virtual COM Port will receive data from an OpenBCI USB Dongle.\n\
Yes (y or Enter) or  No (n) \n\n\
Note that you should only need to specify 'n' if there are other devices plugged into the Pi via VCP.\n\
If there are only OpenBCI Dongles plugged in, they should be the only options listed, \
and they should look like 'ttyUSB0', 'ttyUSB1', and so on.\n\n"

# path to VCP devices
dev_path="/sys/bus/usb-serial/devices/"

# Loop through all VCP devices
for entry in "$dev_path"*
do
  while true  # loop until valid input
  do
    read -p "${entry:28}: " answer
    if [ "${answer,}" = "y" ] || [ "${answer}" = "" ]
    then
      # Change FTDI VCP driver latency timer for the read buffer from 16ms to 1ms.
      # This allows data to be read from the dongle smoothly rather than in chunks.
      # (This file is readonly and sudo doesn't work on the redirection operator)
      sudo sh -c "echo 1 > $entry/latency_timer"
      break
    elif [ "${answer,}" = "n" ]
    then
      break
    else  # invalid input
      echo "Invalid input. Type y or n"
    fi
  done
done

cd ./lib
python3 run_pi.py