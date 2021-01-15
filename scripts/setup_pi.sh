#!/usr/bin/env bash
set -e  # exit on error

# ensure that CWD is the directory of this script so we can navigate from here
cd "$(dirname "$0")"
source ./misc.sh  # import loading function

(
# ensure python is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
sudo pip3 install -r ./requirements_pi.txt  # install requirements
) > /dev/null &
loading $! "Installing Python3 and dependent requirements.... \n\
Please wait until this is finished to provide configuration information\n"

python3 ../app/setup_pi.py # Get configuration from user
printf "No further interaction is required.\nInstallation will continue, and afterward the Pi will reboot.\n"
sleep 3

(
# Add crontab line to start the app on boot, targetting data-hub/main/run_pi.sh
run_path="$(pwd -P)/run_pi.sh"  # get absolute path of run_pi.sh
(sudo crontab -l ; echo "@reboot sh ${run_path}") 2>/dev/null | sort | uniq | sudo crontab -
) > /dev/null &
loading $! "Writing Crontab line to start the application on boot..."

(
# Enable Picam if not already
if grep "start_x=0" /boot/config.txt
then
  sudo sed -i "s/start_x=0/start_x=1/g" /boot/config.txt
fi
) > /dev/null &
loading $! "Enabled Picam..."

(
# Enable Sense Hat if not already
if ! grep "dtoverlay=rpi-sense" /boot/config.txt
then
  echo "dtoverlay=rpi-sense" | sudo tee -a /boot/config.txt
fi
) > /dev/null &
loading $! "Enabling SenseHat..."

(
# download brainflow
cd ~/ # go to home directory
if [ -d "./brainflow" ]  # if brainflow directory already exists
then
  cd ./brainflow
  git pull https://github.com/OpenBCI/brainflow.git
  cd ..
else
  git clone https://github.com/OpenBCI/brainflow.git
fi

sudo apt-get install cmake -y  # make sure cmake is installed

# build brainflow
cd ./brainflow
bash ./tools/build_linux.sh > /dev/null
sudo pip3 install ./python-package

# for numpy to work properly with brainflow on Raspbian
sudo apt-get -y install libatlas-base-dev
) > /dev/null &
loading $! "Installing and building Brainflow in home directory... (may take a while)"

