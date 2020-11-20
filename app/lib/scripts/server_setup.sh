#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"  # directory of script

sudo apt-get -y install python3
sudo apt-get -y install python3-pip
pip3 install -r ./server_requirements.txt

echo DONE