#!/usr/bin/env bash

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir

# update from git
#echo "Updating From Git..."
#git pull

# kill any remaining processed
bash quit.sh

bash run_stream.sh

bash run_server.sh

