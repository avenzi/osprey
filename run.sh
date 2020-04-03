#!/bin/bash
pkill gunicorn
gunicorn --bind 0.0.0.0:5000 --threads 10 capstone:app