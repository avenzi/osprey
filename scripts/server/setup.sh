#!/usr/bin/env bash

# ensure that CWD is the directory of this script so we can navigate from here
script_dir="$(dirname $(realpath $0))"
cd $script_dir
source ../misc.sh  # import loading function

# make sure pkg-config is installed
sudo apt-get install pkg-config -y

# compile redis from source
curl -s -o redis-stable.tar.gz "http://download.redis.io/redis-stable.tar.gz"
sudo mkdir -p /usr/local/lib/
sudo chmod a+w /usr/local/lib/
sudo tar -C /usr/local/lib/ -xzf redis-stable.tar.gz
sudo rm redis-stable.tar.gz
cd /usr/local/lib/redis-stable/
sudo make
sudo make install

# navigate back to top level dir (where venv will go)
cd $script_dir/../../
(
#ensure python is installed
#sudo apt-get -y install python3
#sudo apt-get -y install python3-pip
python3 -m venv venv
. venv/bin/activate
pip3 install -r scripts/server/python_requirements.txt  # install requirements (don't use sudo in venv!)
) #> /dev/null &
#loading $! "Installing Python3 and dependent requirements.... \n\
#Please wait until this is finished to provide configuration information\n"

. venv/bin/activate
python3 lib/setup_server.py # Get configuration from user
exit