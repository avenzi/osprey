#!/usr/bin/env bash
# This is the file targeted by cron on boot

# ensure the CWD is the directory of this script
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

# update from git
#echo "Updating From Git..."
#git pull

# kill any remaining python processes
#sudo pkill python3
#sudo pkill python

# run python file to start the client
. venv/bin/activate
# can't run with sudo, or it won't be run inside virtual environment.
# This might mess up acessing certain files from with the program, though.
python3 -m lib.raspi.run_pi