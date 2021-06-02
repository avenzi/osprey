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

# run python in background
python3 -m lib.server.run_analysis &

# start redis server
redis-server config/redis.conf

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn.conf.py "app:create_app()"

