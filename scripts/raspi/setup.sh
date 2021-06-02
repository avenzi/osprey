#!/usr/bin/env bash
set -e  # exit on error

# ensure that CWD is the directory of this script so we can navigate from here
script_dir="$(dirname $(realpath $0))"
cd $script_dir
source ../misc.sh  # import loading function
# navigate to top level dir
cd ../../

(
# ensure python is installed
#sudo apt-get -y install python3
#sudo apt-get -y install python3-pip
python3 -m venv venv
. venv/bin/activate
pip3 install -r scripts/raspi/python_requirements.txt  # install requirements (don't use sudo in venv!)
) #> /dev/null &
#loading $! "Installing Python3 and dependent requirements.... \n\
#Please wait until this is finished to provide configuration information\n"

. venv/bin/activate
python3 lib/setup_pi.py # Get configuration from user
printf " > No further interaction is required.\nInstallation will continue, and afterward the Pi will reboot.\n"
sleep 3

# Add crontab line to start the app on boot, targetting data-hub/main/run.sh
echo "Writing Crontab line to start the application on boot..."
run_path="$(pwd -P)/run.sh"  # get absolute path of run.sh
(sudo crontab -l ; echo "@reboot sh ${run_path}") 2>/dev/null | sort | uniq | sudo crontab -

# Enable Picam if not already
echo "> Enabling Picam..."
if grep "start_x=0" /boot/config.txt
then
  sudo sed -i "s/start_x=0/start_x=1/g" /boot/config.txt
fi

# Enable Sense Hat if not already
echo "> Enabling Sense Hat..."
if ! grep "dtoverlay=rpi-sense" /boot/config.txt
then
  echo "dtoverlay=rpi-sense" | sudo tee -a /boot/config.txt
fi

(
# for numpy to work properly with brainflow on Raspbian
sudo apt-get -y install libatlas-base-dev

. venv/bin/activate  # actuvate vitualenv
# download and install brainflow from source (otherwise doesn't work on Pi)
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
pip3 install -U ./python-package

) > /dev/null &
loading $! "> Installing and building Brainflow in home directory... (may take a while)"

