#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# kill any remaining processed
pkill gunicorn
pkill redis-server

# start redis server for streaming
redis-server config/live_redis.conf

# start redis server for Flask session store
redis-server config/session_redis.conf

# Run Nginx with custom config (needs absolute path to config)
nginx -c ${script_dir}/../../config/nginx.conf

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn.conf.py "app:create_app()"

