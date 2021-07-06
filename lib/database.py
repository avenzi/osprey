from time import time, sleep, strftime, localtime
import functools
import json
from os import system, path

import redis


def get_time():
    """ Return human readable time for file names """
    return strftime("%m-%d-%Y_%H:%M:%S", localtime())


class DatabaseError(Exception):
    """ invoked when the connection fails when performing a read/write operation """
    pass


def maintain_connection(method):
    """
    Method wrapper to catch some disconnection issues
    Also throws custom error that can be caught in an outer scope
    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if not self.redis:
            if not self.connect():  # attempt to connect
                raise self.Error('Could not connect to database.')

        while not self.exit:
            try:  # attempt to perform database operation
                return method(self, *args, **kwargs)
            except (redis.exceptions.ConnectionError, ConnectionResetError, ConnectionRefusedError)as e:
                if self.connect():  # attempt to connect
                    continue
                else:
                    raise self.Error('Database connection error: {}'.format(e))
            except Exception as e:
                raise self.Error('Error in Database ({}). {}: {}'.format(method.__name__, e.__class__.__name__, e))
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

        # file paths
        self.file_path = 'data/dump.rdb'  # main database file to read from
        self.store_path = 'data/redis_dumps'  # directory of old files

        # Separate redis pools for reading decoded data or reading raw bytes data.
        # not sure how to give Redis instances to certain sessions.
        self.pool = redis.ConnectionPool(host=ip, port=port, password=password, decode_responses=True)
        self.bytes_pool = redis.ConnectionPool(host=ip, port=port, password=password, decode_responses=False)
        self.redis = redis.Redis(connection_pool=self.pool)
        self.bytes_redis = redis.Redis(connection_pool=self.bytes_pool)

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
        # move old file if it's there
        try:
            system("redis-server config/redis.conf")
            self.exit = False
        except Exception as e:
            raise DatabaseError("Failed to initialize database: {}".format(e))

    def shutdown(self, filename=None):
        """ Shut down database process and save data """
        if not self.redis:
            return False
        try:
            self.redis.shutdown(save=True)

            # if file name not given or already exists
            if not filename or path.isfile(self.store_path+filename):
                print("Filename not specified or already exists - using default timestamp.")
                filename = get_time()

            # move current dump file to storage directory with new name
            system("mv {} {}/{}.rdb".format(self.file_path, self.store_path, filename))
            # TODO: Make a copy of the file, but don't remove the current one, then wipe the whole database.
            #  This might avoid problems with shutting it down entirely.
            self.disconnect()
            return True

        except Exception as e:
            raise DatabaseError("Failed to shutdown or save database: {}".format(e))

    def load_file(self, filename):
        """ Loads in the specified redis dump file and starts the redis server """
        self.shutdown()  # shut down current database file if it exists

        try:
            # remove current data file if it exists.
            # it shouldn't (because of shutdown()) but this is just in case.
            system('rm {}'.format(self.file_path))
        except:
            pass

        try:
            system("cp {}/{} {}".format(self.store_path, filename, self.file_path))
            self.init()
        except Exception as e:
            raise DatabaseError("Failed to load file to database: {}".format(e))

    def rename_save(self, filename, newname):
        """ renames an old save file """
        print("OLD: {}, NEW: {}".format(filename, newname))
        # todo: implement this

    def delete_save(self, filename):
        """ Remove an old stored file """
        try:
            system('rm {}/{}'.format(self.store_path, filename))
        except Exception as e:
            raise DatabaseError("Failed to delete file: {}".format(e))

    def connect(self, timeout=None, delay=1):
        """
        Attempt to connect to database
        <timeout> Time until error returned. None never stops.
        <delay> Delay in seconds before repeating each time
        """
        start = time()
        t = 0
        while not self.exit:  # until node exits
            try:
                self.redis = redis.Redis(connection_pool=self.pool)
                self.bytes_redis = redis.Redis(connection_pool=self.bytes_pool)
                self.redis.ping()
                self.bytes_redis.ping()
            except Exception as e:
                if timeout is None or time()-start < timeout:
                    t += 1
                    sleep(delay)
                    continue
                else:
                    return False
            return True  # successful ping

    def disconnect(self):
        """ Disconnect from database """
        self.exit = True
        self.redis = None
        self.bytes_redis = None

    def ping(self):
        """ Ping database to ensure connecting is functioning """
        try:
            if self.redis.ping():
                return True
        except:
            return False

    @maintain_connection
    def write_data(self, stream, data):
        """
        Writes time series <data> to stream:<stream>.
        if <data> is a dictionary of items where keys are column names.
        items must either all be iterable or all non-iterable.
        """
        if hasattr(type(list(data.values())[0]), '__iter__'):  # if an iterable sequence of data points
            pipe = self.redis.pipeline()  # pipeline queues a series of commands at once
            max_length = 0  # get the size of the longest column
            for val in data.values():
                length = len(val)
                if length > max_length:
                    max_length = length

            for i in range(max_length):
                d = {}
                for key, val in data.items():
                    if len(val) <= i:
                        continue
                    d[key] = data[key][i]
                pipe.xadd('stream:'+stream, d)

            pipe.execute()
        else:  # assume this is a single data point
            self.redis.xadd('stream:'+stream, {key: data[key] for key in data.keys()})

    @maintain_connection
    def read_data(self, stream, reader, count=None, max_time=None, numerical=True, to_json=False, decode=True):
        """
        Gets newest data for <reader> from data column <stream>.
        <stream> is some ID that identifies the stream in the database.
        <reader> is some ID that will keep track of it's own read head position.
        <count> is the number of data points to read (ignoring whether the point have already been read.
            - If None, read as many new points as possible.
            - If not None, ignores <max_time> an <reader>
        <max_time> maximum time window (s) to read. (If count is None).
            - If None, read as much as possible (guarantees all data read)
        <numerical>  Whether the data needs to be converted python float type
        <decode> Whether to decode the result into strings.
            If False, only values will remain as bytes. Keys will still be decoded.
        <to_json> whether to convert to json string. if False, uses dictionary of lists.
        """
        if decode:
            red = self.redis
        else:
            numerical = False
            red = self.bytes_redis

        if stream is None or reader is None:
            return

        bookmarks = self.bookmarks.get(reader)  # get reader-specific bookmarks
        if not bookmarks:  # this reader hasn't read before
            bookmarks = {}
            self.bookmarks[reader] = bookmarks

        if count:  # get COUNT data regardless of last read
            response = red.xrevrange('stream:'+stream, count=count)

        else:  # get data since last read
            last_read = bookmarks.get(stream)
            if last_read:  # last read spot exists
                if max_time:  # max time window set
                    # furthest back time stamp to read
                    # put into same format as redis time stamp (integer milliseconds)
                    limit = int(1000*(time()-max_time))
                    last_read = last_read if int(last_read.split('-')[0]) > limit else limit
                response = red.xread({'stream:'+stream: last_read})
            else:  # no last spot, start reading from latest, block for 1 sec
                response = red.xread({'stream:'+stream: '$'}, block=1000)

        if not response:
            return None

        # store the last ID of this stream and get list of data dicts
        if count:
            self.bookmarks[reader][stream] = response[-1][0]
            data_list = response
        else:
            self.bookmarks[reader][stream] = response[0][1][-1][0]
            data_list = response[0][1]

        # create final output dict
        output = {}

        # loop through stream data and convert if necessart

        # I hate this
        if numerical and decode:
            for data in data_list:
                d = data[1]  # data dict. data[0] is the timestamp ID
                for key in d.keys():
                    if output.get(key):
                        output[key].append(float(d[key]))  # convert to float and append
                    else:
                        output[key] = [float(d[key])]

        elif numerical and not decode:
            for data in data_list:
                d = data[1]  # data dict. data[0] is the timestamp ID
                for key in d.keys():
                    k = key.decode('utf-8')  # key won't be decoded, but it needs to be
                    if output.get(k):
                        output[k].append(float(d[key]))  # convert to float and append
                    else:
                        output[k] = [float(d[key])]

        elif not numerical and decode:
            for data in data_list:
                # data[0] is the timestamp ID
                d = data[1]  # data dict
                for key in d.keys():
                    if output.get(key):
                        output[key].append(d[key])  # append
                    else:
                        output[key] = [d[key]]

        elif not numerical and not decode:
            for data in data_list:
                # data[0] is the timestamp ID
                d = data[1]  # data dict
                for key in d.keys():
                    k = key.decode('utf-8')  # key won't be decoded, but it needs to be
                    if output.get(k):
                        output[k].append(d[key])  # append
                    else:
                        output[k] = [d[key]]

        if to_json:
            return json.dumps(output)
        return output

    @maintain_connection
    def write_snapshot(self, stream, data):
        """
        Writes a snapshot of data <data> to stream:<stream>.
        <data> must be a dictionary of lists, where keys are data column names.
        Note that this method is for data which is not consecutive (like time series).
        It is for data that is meant to be viewed a chunk at a time.
        It places each list of data values as a comma separated list under one key.
        """
        new_data = {}
        for key in data.keys():
            new_data[key] = ','.join(str(val) for val in data[key])

        self.redis.xadd('stream:'+stream, new_data)

    @maintain_connection
    def read_snapshot(self, stream, to_json=False, decode=True):
        """
        Gets latest snapshot for <reader> from data column <stream>.
        <stream> is some ID that identifies the stream in the database.
        <to_json> whether to convert to json string. if False, uses dictionary of lists.
        Since this is a snapshot (not time series), gets last 1 data point from redis
        """
        if decode:
            red = self.redis
        else:
            red = self.bytes_redis

        response = red.xrevrange('stream:'+stream, count=1)
        if not response:
            return None

        data = response[0][1]  # data dict
        keys = data.keys()  # get keys from data dict
        output = {key: [] for key in keys}

        for key in keys:
            vals = data[key].split(',')
            output[key] = [float(val) for val in vals]

        if to_json:
            return json.dumps(output)
        return output

    @maintain_connection
    def write_info(self, key, data):
        """
        Writes <data> to info:<key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('info:'+key, data)

    @maintain_connection
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

    @maintain_connection
    def read_all_info(self):
        """ Gets a list of dictionaries containing info for all connected streams """
        info = []
        for key in self.redis.execute_command('keys info:*'):
            info.append(self.redis.hgetall(key))
        return info

    @maintain_connection
    def write_group(self, key, data):
        """
        Writes <data> to group:<key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('group:'+key, data)

    @maintain_connection
    def read_group(self, name, stream=None):
        """
        Gets an info dict from stream with name <stream> in group_name <name>
        if <name> not specified, gives list of all dicts in that group
        """
        if stream is not None:  # stream name specified
            stream_id = self.redis.hget('group:'+name, stream)  # get stream ID from group dict
            return self.read_info(stream_id)  # return dict for that stream

        else:  # no stream name specified - get whole group
            data = {}  # name: {stream info dict}
            group = self.redis.hgetall('group:'+name)  # name:ID
            for key in group.keys():  # for each stream name
                data[key] = self.read_info(group[key])
            return data

    @maintain_connection
    def read_all_groups(self):
        """ Gets a list of dictionaries containing name and ID info for all connected streams """
        info = []
        for key in self.redis.execute_command('keys group:*'):
            info.append(self.redis.hgetall(key))
        return info







