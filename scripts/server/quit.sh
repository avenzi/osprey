#!/usr/bin/env bash

sudo pkill python
sudo pkill python3
sudo pkill gunicorn
sudo pkill redis-server
sudo fuser -k 80/tcp    # Nginx
sudo fuser -k 5000/tcp  # Flask server
sudo fuser -k 5001/tcp  # Redis database server
sudo fuser -k 5002/tcp
sudo fuser -k 6379/tcp  # Redis session server