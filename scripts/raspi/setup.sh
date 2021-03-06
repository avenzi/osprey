#!/usr/bin/env bash
set -e  # exit on error

# ensure that CWD is the directory of this script so we can navigate from here
script_dir="$(dirname $(realpath $0))"
cd $script_dir
source ../misc.sh  # import loading function
# navigate to top level dir
cd ../../

# ensure python is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
python3 -m venv venv
. venv/bin/activate
pip3 install -r scripts/raspi/python_requirements.txt  # install requirements (don't use sudo in venv!)

# Add crontab line to start the app on boot, targetting data-hub/main/run_all.sh
echo "Writing Crontab line to start the application on boot..."
run_path="$(pwd -P)/run.sh"  # get absolute path of run_all.sh
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

# for numpy to work properly with brainflow on Raspbian
sudo apt-get -y install libatlas-base-dev

# make sure cmake is installed
sudo apt-get install cmake -y

. venv/bin/activate  # actuvate vitualenv

# download and install brainflow from source (otherwise doesn't work on Pi)
cd ~/ # go to home directory
if [ -d "./brainflow" ]  # if brainflow directory already exists
then
  echo "Brainflow Repo found"
  cd ./brainflow
  if ! git diff --quiet origin/master; then  # if the git repo needs to update
    echo "Brainflow repo needs to update."
    git pull https://github.com/OpenBCI/brainflow.git
    echo "Building Brainflow."
    bash ./tools/build_linux.sh > /dev/null  # build brainflow
    pip3 install -U ./python-package  # install package to virtual env
  else
    echo "Brainflow already up-to-date."
  fi
else
  echo "Brainflow not found."
  git clone https://github.com/OpenBCI/brainflow.git
  cd ./brainflow
  echo "Building Brainflow."
  bash ./tools/build_linux.sh > /dev/null  # build brainflow
  pip3 install -U ./python-package  # install package to virtual env
fi

echo "Done."





