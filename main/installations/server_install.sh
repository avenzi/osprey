#!/bin/bash
pip3 install -r server_requirements.txt

# BRAINFLOW
# only needed as long as using brainflow data filtering/denoising on the server
cd ~/
git clone https://github.com/OpenBCI/brainflow.git
sudo apt-get install cmake -y

cd ./brainflow
bash ./tools/build_linux.sh
pip3 install ./python-package