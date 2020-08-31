#!/bin/bash
pip3 install -r requirements.txt

# BRAINFLOW
cd ~/
git clone https://github.com/OpenBCI/brainflow.git
sudo apt-get install cmake -y

cd ./brainflow
bash ./tools/build_linux.sh
pip3 install ./python-package

# for numpy to work properly on Raspbian (Required for brainflow)
sudo apt-get install libatlas-base-dev