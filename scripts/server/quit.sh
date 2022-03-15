#!/usr/bin/env bash

pkill python
pkill python3
pkill gunicorn
pkill redis-server
fuser -k 80/tcp    # Nginx
fuser -k 5000/tcp  # Flask server
fuser -k 5001/tcp  # Redis database server
fuser -k 5002/tcp
fuser -k 6379/tcp  # Redis session server