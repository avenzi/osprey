#!/bin/bash
cd site
gunicorn --bind 0.0.0.0:5000 capstone:app