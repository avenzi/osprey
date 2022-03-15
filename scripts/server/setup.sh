#!/usr/bin/env bash

# compile redis from source
curl -s -o redis-stable.tar.gz "http://download.redis.io/redis-stable.tar.gz"
mkdir -p /usr/local/lib/
tar -C /usr/local/lib/ -xzf redis-stable.tar.gz
rm redis-stable.tar.gz
cd /usr/local/lib/redis-stable/
make
make install