#!/usr/bin/env bash

sudo pkill python
sudo pkill python3
sudo pkill gunicorn
sudo pkill redis-server
sudo fuser -k 5000/tcp  # clear activity on port 5000
sudo fuser -k 5001/tcp  # clear activity on port 5001
sudo fuser -k 5002/tcp  # clear activity on port 5002