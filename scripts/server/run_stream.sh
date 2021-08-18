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
sudo pkill python3

# activate virtual environment and run
. venv/bin/activate
python3 -m server.run_streamers


