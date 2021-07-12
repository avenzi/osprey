#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# update from git
#echo "Updating From Git..."
#git pull

# kill any remaining processed
bash scripts/server/quit.sh

# activate virtual environment
. venv/bin/activate

# run python in background
python3 -m local.run_analysis &

# start redis server for streaming
redis-server config/live_redis.conf

# start redis server for Flask session store
redis-server config/session_redis.conf

# call gunicorn with appropriate config file
gunicorn -c config/gunicorn.conf.py "app:create_app()"

