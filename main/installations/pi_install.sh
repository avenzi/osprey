#!/bin/bash

# Specify COM port
printf "Please specify the Virtual COM Port assigned to the USB Dongle used to stream EEG data. \nBy defaul this is 'ttyUSB0' \nIf this does not need to be changed, press enter to skip.\n"
read -p 'VCP: ' comport
if [ "$comport" = "" ]; then
    comport="ttyUSB0"  # default
fi

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"  # go to directory of this script

# ensure python stuff is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
pip3 install -r ./pi_requirements.txt

# download brainflow
cd ~/
git clone https://github.com/OpenBCI/brainflow.git
sudo apt-get install cmake -y

# build brainflow
cd ./brainflow
bash ./tools/build_linux.sh
pip3 install ./python-package

# for numpy to work properly on Raspbian (Required for brainflow)
sudo apt-get -y install libatlas-base-dev

# Change FTDI driver settings to allow for data to be
# taken at smooth intervals rather than being 'chunked'.
# The default value in this file is 16, we are changing it to 1.
# (This file is readonly and sudo doesn't work on redirections)
sudo sh -c "echo 1 > /sys/bus/usb-serial/devices/$comport/latency_timer"

# Enable Picam
echo Enabling Picam...
if grep "start_x=0" /boot/config.txt
then
  sudo sed -i "s/start_x=0/start_x=1/g" /boot/config.txt || exit
  sudo reboot
else
  exit
fi