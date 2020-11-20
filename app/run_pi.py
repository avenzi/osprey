import os

# ensure that python's CWD is this script's directory
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# run run_pi.py to start the client
import lib.raspi.run_pi