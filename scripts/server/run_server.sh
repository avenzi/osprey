#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# kill any remaining processed
sudo pkill gunicorn
sudo pkill redis-server
sudo fuser -k 5000/tcp  # clear activity on port 5000
sudo fuser -k 5001/tcp  # clear activity on port 5001
sudo fuser -k 5002/tcp  # clear activity on port 5002
sudo fuser -k 6379/tcp  # clear activity on port 6379

# start redis server for streaming
redis-server config/live_redis.conf

# start redis server for Flask session store
redis-server config/session_redis.conf

# activate virtual environment
. venv/bin/activate

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn.conf.py "app:create_app()"

