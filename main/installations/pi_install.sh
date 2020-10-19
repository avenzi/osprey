#!/bin/bash

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

# Enable Picam
echo Enabling Picam...
if grep "start_x=0" /boot/config.txt
then
  sudo sed -i "s/start_x=0/start_x=1/g" /boot/config.txt || exit
  sudo reboot
else
  exit
fi