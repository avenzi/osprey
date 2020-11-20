#!/usr/bin/env bash
set -e  # exit on error
source ./misc.sh  # import loading function

# get directory of this script
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

(
# ensure python is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
pip3 install -r ./pi_requirements.txt  # install requirements
) > /dev/null &
loading $! "Installing Python3 and dependent requirements. \n\
Please wait until this is finished to provide configuration information\n..."

# Get configuration from user
python3 ./../raspi/pi_config.py

printf "No further interaction is required.\nInstallation will continue, and afterward the Pi will reboot."
sleep 5

(
# Add crontab line to start the app on boot, targetting data-hub/main/run_pi.sh
cd "../../"  # move out to data-hub/main
run_path="$(pwd -P)/run_pi.sh"
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
# download brainflow
cd ~/ # go to home directory
git clone https://github.com/OpenBCI/brainflow.git
sudo apt-get install cmake -y

# build brainflow
cd ./brainflow
bash ./tools/build_linux.sh
pip3 install ./python-package

# for numpy to work properly with brainflow on Raspbian
sudo apt-get -y install libatlas-base-dev
) > /dev/null &
loading $! "Installing and building Brainflow in home directory... (might take a while)"

