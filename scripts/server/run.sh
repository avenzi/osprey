#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# update from git
#echo "Updating From Git..."
#git pull

# kill any remaining python processes
sudo pkill python
sudo pkill python3
sudo pkill gunicorn
sudo pkill redis-server
sudo fuser -k 5000/tcp  # clear activity on port 5000
sudo fuser -k 5001/tcp  # clear activity on port 5001
sudo fuser -k 5002/tcp  # clear activity on port 5002

# activate virtual environment
. venv/bin/activate

# start redis server
redis-server config/redis.conf

# run data transfer application (in background) and dump to log file
python3 data_transfer_lib/run_server.py #&> logs/data_tramsfer.log &

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn_prod.conf.py "app.__init__:create_app()"
