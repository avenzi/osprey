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

# Clone or Update RedisTimeSeries
# TODO: don't know if I'll end up using RedisTimeSeries. Remove this if not
cd ~
if [ ! -d "RedisTimeSeries" ] ; then
    git clone --recursive https://github.com/RedisTimeSeries/RedisTimeSeries.git
    cd "RedisTimeSeries"
else
    cd "RedisTimeSeries"
    git pull https://github.com/RedisTimeSeries/RedisTimeSeries.git
fi

# build RedisTimeSeries
sudo make setup
sudo make build

# navigate back to top level dir (where venv will go)
cd $script_dir/../../
(
#ensure python is installed
sudo apt-get -y install python3
sudo apt-get -y install python3-pip
python3 -m venv venv
. venv/bin/activate
pip3 install -r scripts/server/python_requirements.txt  # install requirements (don't use sudo in venv!)
) #> /dev/null &
#loading $! "Installing Python3 and dependent requirements.... \n\
#Please wait until this is finished to provide configuration information\n"

# install nginx
sudo apt-get -y install nginx
# Get PPA for CertBot
sudo add-apt-repository ppa:certbot/certbot -y
sudo apt-get update
sudo apt-get install python-certbot-nginx -y

# ffmpeg
sudo apt-get install ffmpeg -y

echo "Writing Crontab line to renew SSl certification..."
webroot="$(pwd -P)/app"  # get absolute path to website root
echo ${webroot}
(sudo crontab -l ; echo "0 12 * * * sudo certbot renew --webroot -w ${webroot}") 2>/dev/null | sort | uniq | sudo crontab -

echo "Done!"
exit