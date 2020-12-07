#!/usr/bin/env bash

# ensure that CWD is the directory of this script so we can navigate from here
cd "$(dirname "$0")"
source ./misc.sh  # import loading function

(
# ensure python is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
pip3 install -r ./requirements_server.txt  # install requirements
) > /dev/null &
loading $! "Installing Python3 and dependent requirements.... \n\
Please wait until this is finished to provide configuration information\n"

python3 ../app/setup_server.py # Get configuration from user