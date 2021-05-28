from time import sleep
from datetime import datetime
import functools
import json
import os

import redis
from redis.exceptions import ConnectionError


def get_time():
    """ Return human readable time for file names """
    return datetime.now().strftime("%-H:%-M:%-S:%f")


class DatabaseError(Exception):
    """ invoked when the connection fails when performing a read/write operation """
    pass


def handle_errors(method):
    """ method wrapper to throw custom errors """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if not self.redis:
            raise self.Error('Database not initialized. Use database.connect() first.')
        try:
            return method(self, *args, **kwargs)
        except redis.ConnectionError as e:
            raise self.Error('Database connection error: {}'.format(e))
    return wrapped


class Database:
    """
    Wrapper class to handle a connection to a database.
    Uses reference to the handling node class to monitor an exit_condition.
    Current written with Redis.
    """
    Error = DatabaseError

    def __init__(self, ip, port, password):
        super().__init__()
        self.redis = None
        self.ip = ip  # ip of database
        self.port = port  # database port
        self.password = password  # database password

        self.exit = False  # flag to determine when to stop running if looping

    def init(self):
        """ Initialize database process """
        os.system("redis-server config/redis.conf")

    def shutdown(self):
        """ Shut down database process and save data """
        if not self.redis:
           return
        try:
            self.redis.shutdown(save=True)
            os.system("mv data/dump.rdb data/redis_dumps/{}.rdb".format(get_time()))
            self.redis = None
            return True
        except Exception as e:
            print("Failed to shutdown or save database: {}".format(e))
            return False

    def connect(self, repeat=None, delay=1):
        """
        Attempt to connect to database
        <repeat> Max number of retries. Infinitely loops if None.
        <delay> Delay in seconds before repeating each time
        """
        tries = 0
        while not self.exit:  # until node exits
            try:
                self.redis = redis.Redis(host=self.ip, port=self.port, password=self.password, decode_responses=True)
                if self.redis.ping():
                    return True
            except Exception as e:
                if repeat is None or tries < repeat:
                    tries += 1
                    sleep(delay)
                else:
                    return False

    def disconnect(self):
        """
        Disconnect from database
        Redis uses pools and doesn't require an explicit disconnect
        """
        self.exit = True

    def ping(self):
        """ Ping database to ensure connecting is functioning """
        try:
            if self.redis.ping():
                return True
        except:
            return False

    @handle_errors
    def read_data(self, stream, to_json=False):
        """
        Gets newest data from data column <stream>.
        <to_json> whether to convert to json string. if False, uses dictionary of lists
        Redis uses '$' to denote most recent data ID.
        """
        stream = self.redis.xread({'stream:'+stream: '$'}, None, 0)  # BLOCK 0
        if not stream:
            return None

        # get keys, which are every other element in first data list
        keys = stream[0][1][0][1].keys()
        output = {key: [] for key in keys}

        # loop through stream data
        for data in stream[0][1]:
            # data[0] is the timestamp ID
            d = data[1]  # data dict
            for key in keys:
                output[key].append(float(d[key]))  # convert to float and append

        if to_json:
            return json.dumps(output)
        return output

    @handle_errors
    def read_data_since(self, stream, last_read, to_json=False):
        """
        Gets data since <last_read> ID from data column <stream>.
        <to_json> whether to convert to json string. If False, outputs a dictionary of lists.
        Redis uses '$' to denote most recent data ID.
        Returns a tuple of data and last read ID.
        """
        if not last_read:  # get last ID if not given
            last_read = self.redis.xrevrange('stream:'+stream, count=1)[0][0]

        stream = self.redis.xread({'stream:'+stream: last_read})
        if not stream:
            return None, last_read

        last_read = stream[0][1][-1][0]  # last ID from stream

        # get keys, which are every other element in first data list
        keys = stream[0][1][0][1].keys()
        output = {key: [] for key in keys}

        # loop through stream data
        for data in stream[0][1]:
            # data[0] is the timestamp ID
            d = data[1]  # data dict
            for key in keys:
                output[key].append(float(d[key]))  # convert to float and append

        if to_json:
            output = json.dumps(output)
        return output, last_read

    @handle_errors
    def write_data(self, stream, data):
        """
        Writes <data> to <stream>.
        <data> must be a dictionary of lists, where keys are data column names.
        """
        pipe = self.redis.pipeline()  # pipeline queues a series of commands at once
        for i in range(len(data[list(data.keys())[0]])):  # get length of a random key (all the same)
            # get slice of each data point as dictionary
            pipe.xadd('stream:'+stream, {key: data[key][i] for key in data.keys()})
        pipe.execute()

    @handle_errors
    def read_info(self, key, name):
        """
        Reads <name> from map with key <key>
        """
        return self.redis.hget('info:'+key, name)

    @handle_errors
    def write_info(self, key, data):
        """
        Writes <data> to <key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('info:'+key, data)

    @handle_errors
    def get_info_keys(self):
        """ Gets a list of all info keys """
        stream_names = []
        for key in self.redis.execute_command('keys info:*'):
            stream_names.append(self.redis.hget(key, 'name'))
        return stream_names




