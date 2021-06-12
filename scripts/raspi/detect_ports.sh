#!/usr/bin/env bash
set -e  # exit on error

# ensure that CWD is the directory of this script so we can navigate from here
script_dir="$(dirname $(realpath $0))"
cd $script_dir
# navigate to top level dir
cd ../../

python3 -m lib.raspi.detect_ports
