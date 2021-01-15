#!/usr/bin/env bash
# This is the file targeted by cron on boot

# ensure the CWD is the directory of this script
cd "$(dirname "$0")"

# update from git
echo "Updating From Git..."
git pull

# kill any remaining python processes
sudo pkill python3
sudo pkill python

# run python file to start the client
sudo python3 ../app/run_pi.py