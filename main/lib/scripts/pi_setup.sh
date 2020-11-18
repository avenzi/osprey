#!/bin/bash
set -e  # exit on error


# get directory of this script
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"


{  # ensure python stuff is installed
echo "Making sure Python-3 is up to date..."
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
pip3 install -r ./pi_requirements.txt
} > /dev/null  # silence stout

# Add crontab line to start the app on boot, targetting data-hub/main/run_pi.sh
cd "../../"  # move out data-hub/main
run_path="$(pwd -P)/run_pi.sh"
(sudo crontab -l ; echo "@reboot sh ${run_path}") 2>/dev/null | sort | uniq | sudo crontab -

{  # download brainflow
cd ~/ # go to home directory
git clone https://github.com/OpenBCI/brainflow.git
sudo apt-get install cmake -y
} > /dev/null  # silence stout

# build brainflow
cd ./brainflow
bash ./tools/build_linux.sh
pip3 install ./python-package

# for numpy to work properly with brainflow on Raspbian
sudo apt-get -y install libatlas-base-dev

# Enable Picam
echo Enabling Picam...
if grep "start_x=0" /boot/config.txt
then
  sudo sed -i "s/start_x=0/start_x=1/g" /boot/config.txt
fi

