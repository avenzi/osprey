#!/usr/bin/env bash
# This is the file targeted by cron on boot

# ensure the CWD is the directory of this script
cd "$(dirname "$0")"

# update from git
git pull

# run python file to start the client
python3 ../app/run_pi.py