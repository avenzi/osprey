#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../
echo pwd

# kill any remaining processed
bash scripts/server/quit.sh

# activate virtual environment
. venv/bin/activate

# call gunicorn with appropriate config file
gunicorn -c nbinx_test/gunicorn.conf.py "nginx_test:create_app()"

