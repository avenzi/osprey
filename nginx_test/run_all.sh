#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../

# kill any remaining processed
sudo pkill python
sudo pkill python3
sudo pkill gunicorn
sudo fuser -k 5000/tcp  # clear activity on port 5000
sudo fuser -k 80/tcp  # clear activity on port 80

# start nginx with custom config file
sudo nginx -c "${script_dir}/nginx.conf"

# activate virtual environment
. venv/bin/activate

# call gunicorn with appropriate config file
gunicorn -c nginx_test/gunicorn.conf.py "nginx_test:create_app()"

