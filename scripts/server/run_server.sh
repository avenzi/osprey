#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# kill any remaining processed
sudo pkill gunicorn
sudo pkill redis-server

# clear port activity
sudo fuser -k 80/tcp  # Nginx
sudo fuser -k 5000/tcp  # flask app
sudo fuser -k 5001/tcp  # redis database
sudo fuser -k 5002/tcp
sudo fuser -k 6379/tcp  # Redis session server

# start redis server for streaming
redis-server config/live_redis.conf

# start redis server for Flask session store
redis-server config/session_redis.conf

# Run Nginx with custom config
sudo nginx -c ${script_dir}/config/nginx.conf

# activate virtual environment
. venv/bin/activate

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn.conf.py "app:create_app()"

