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
    """
    Method wrapper to catch some disconnection issues
    Also throws custom errors that can be caught in an outer scope
    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if not self.redis:
            if not self.connect(repeat=1):  # attempt to connect once
                raise self.Error('Could not connect to database')
        try:
            return method(self, *args, **kwargs)
        except redis.ConnectionError as e:
            if self.connect(repeat=1):  # attempt to connect once
                return method(self, *args, **kwargs)
            else:  # failed
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
        self.ip = ip  # ip of database
        self.port = port  # database port
        self.password = password  # database password

        # not sure how to give Redis instances to certain sessions.
        self.pool = redis.ConnectionPool(host=ip, port=port, password=password, decode_responses=True)
        self.redis = redis.Redis(connection_pool=self.pool)

        self.exit = False  # flag to determine when to stop running if looping

        # For different threads to keep track of their own last read operation point.
        # Dictionary of dictionaries: First level key is ID of each separate reader.
        # Each of those dictionaries has keys for each stream in the database, with values
        # of the last stream ID read from it.
        self.bookmarks = {}

    def init(self):
        """
        Initialize database process.
        Obviously only used on the machine that is hosting the redis server
        """
        os.system("redis-server config/redis.conf")
        self.exit = False

    def shutdown(self):
        """ Shut down database process and save data """
        self.exit = True
        if not self.redis:
            return False
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
                self.redis = redis.Redis(connection_pool=self.pool)
                if self.redis.ping():
                    return True
            except ConnectionError as e:
                if repeat is None or tries < repeat:
                    tries += 1
                    sleep(delay)
                else:
                    return False

    def ping(self):
        """ Ping database to ensure connecting is functioning """
        try:
            if self.redis.ping():
                return True
        except:
            return False

    @handle_errors
    def read_data(self, reader, stream, count=None, to_json=False):
        """
        Gets newest data for <reader> from data column <stream>.
        <reader> is some ID that will keep track of it's own read head position.
        <stream> is some ID that identifies the stream in the database.
        <count> is the number of data points to read (ignoring whether the point have already been read.
            - If None, read as many new points as possible.
        <to_json> whether to convert to json string. if False, uses dictionary of lists.
        """
        bookmarks = self.bookmarks.get(reader)  # get reader-specific bookmarks
        if not bookmarks:  # this reader hasn't read before
            bookmarks = {}
            self.bookmarks[reader] = bookmarks

        if count:  # get COUNT data regardless of last read
            response = self.redis.xread({'stream:' + stream: '0'}, count)

        else:  # get data since last read
            last_read = bookmarks.get(stream)
            if stream.startswith('fourier:'):
                print("LAST READ: {}: {}".format(stream, last_read))
            if last_read:  # last read spot exists
                response = self.redis.xread({'stream:'+stream: last_read})

            else:  # no last spot, start reading from latest, block for 1 sec
                response = self.redis.xread({'stream:'+stream: '$'}, None, 1000)

        if not response:
            return None

        # store the last ID of this stream
        self.bookmarks[reader][stream] = response[0][1][-1][0]

        # get keys from data dict
        keys = response[0][1][0][1].keys()
        output = {key: [] for key in keys}

        # loop through stream data
        for data in response[0][1]:
            # data[0] is the timestamp ID
            d = data[1]  # data dict
            for key in keys:
                output[key].append(float(d[key]))  # convert to float and append

        if stream.startswith('fourier:'):
            key = list(output.keys())[0]
            print("{}: {}".format(key, len(output[key])))
        if to_json:
            return json.dumps(output)
        return output

    @handle_errors
    def write_data(self, stream, data):
        """
        Writes <data> to stream:<stream>.
        <data> must be a dictionary of lists, where keys are data column names.
        """
        pipe = self.redis.pipeline()  # pipeline queues a series of commands at once
        for i in range(len(data[list(data.keys())[0]])):  # get length of a random key (all the same)
            # get slice of each data point as dictionary
            pipe.xadd('stream:'+stream, {key: data[key][i] for key in data.keys()})
        pipe.execute()

    @handle_errors
    def read_info(self, ID, name=None):
        """
        Reads <name> from map with key info:<key>
        if <name> not specified, gives dictionary with all key value pairs
        """
        if name is not None:
            return self.redis.hget('info:'+ID, name)
        else:
            data = self.redis.hgetall('info:' + ID)
            return data

    @handle_errors
    def write_info(self, key, data):
        """
        Writes <data> to info:<key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('info:'+key, data)

    @handle_errors
    def get_all_info(self):
        """ Gets a list of dictionaries containing info for all connected streams """
        info = []
        for key in self.redis.execute_command('keys info:*'):
            info.append(self.redis.hgetall(key))
        return info




