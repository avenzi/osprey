import redis
r = redis.Redis(host='127.0.0.1', port=5001, password='thisisthepasswordtotheredisserver')
print(r.ping())
