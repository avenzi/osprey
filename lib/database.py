from time import time, sleep, strftime, localtime
import functools
import json
from os import system, path

import redis


class DatabaseError(Exception):
    """ invoked when the connection fails when performing a read/write operation """
    pass


class DatabaseReadOnly(DatabaseError):
    """ Invoked when the database is not ready to receive write operations """


def get_time_filename():
    """ Return human readable time for file names """
    return strftime("%Y-%m-%d_%H:%M:%S.rdb", localtime())


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


def write_operation(method):
    """
    Method wrapper to throw an error if the database is not ready
    Used for write operations for data
    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if not self.can_write():
            raise DatabaseReadOnly
        method(self, *args, **kwargs)
    return wrapped


class DatabaseController:
    """ Handles connections to multiple different Database instances """
    def __init__(self, live_path, saved_path):
        # index of Database objects
        # keys are ID numbers for each database
        self.sessions = {}

        self.live_ip = '3.131.117.61'
        self.live_path = live_path  # directory of live database dump files

        # index of ports used for playback files and how many Database object connected
        self.playback_ports = {port: {'file':None, 'count':0} for port in [7000, 7001, 7002]}
        self.playback_ip = '3.131.117.61'
        self.save_path = saved_path

    def new_live(self, ip, port, password, file, ID):
        """ Creates and returns a new live Database instance for the given ID key """
        if self.sessions.get(ID):  # Database already associated
            self.remove(ID)  # remove and disconnect
        self.sessions[ID] = ServerDatabase(self.live_ip, port, password, file, self.save_path, live=True)
        print("Created Live database")

    def new_playback(self, file, ID):
        """ Creates and returns a new playback Database instance for the given ID key """
        # iterate through index of ports
        port = None
        for p, info in self.playback_ports.keys():
            if not info['file']:  # this port is available
                port = p
            elif info['file'] == file:  # the port is already associated with the given file
                port = p
                break  # done

        else:  # no port was associated with this file already
            if port is None:  # no ports available
                raise DatabaseError("Could not create new playback server - no ports available")

        self.playback_ports[port]['file'] = file  # set the file for this port if not already
        self.playback_ports[port]['count'] += 1  # increment count of Database classes connecting to this port

        if self.playback_ports[port]['count'] <= 0:
            raise DatabaseError("Error creating playback database - number of redis instances for port {} was negative".format(port))

        if self.sessions.get(ID):  # Database already associated
            self.remove(ID)  # remove and disconnect

        # empty password
        self.sessions[ID] = ServerDatabase(self.playback_ip, port, '', file, self.save_path, live=False)

        count = self.playback_ports[port]['count']
        print("Created new Playback database (#{}) on port: {}".format(count, port))

    def get(self, ID):
        """ Get database by ID """
        return self.sessions.get(ID)

    def remove(self, ID):
        """ Disconnect a Database class and remove it from the dictionary """
        if self.sessions.get(ID):
            db = self.sessions[ID]
            db.disconnect()  # disconnect

            info = self.playback_ports[db.port]
            if info['file'] and info['count'] > 1:  # still some left
                self.playback_ports[db.port]['count'] -= 1  # decrement

            # if a no more databases using this port
            elif info['file'] and info['count'] <= 1:
                self.playback_ports[db.port]['count'] = 0
                self.playback_ports[db.port]['file'] = None  # un-associate file from port

            del self.sessions[ID]  # remove from dict

    def rename_save(self, filename, newname):
        """ renames an old save file """
        if not filename:
            raise Exception("Could not rename file - no file given to rename")
        if not newname:
            newname = get_time_filename()
        if not newname.endswith('.rdb'):
            newname += '.rdb'
        if path.isfile(self.save_path + '/' + newname):
            raise Exception("Could not rename file - file already exists")
        try:
            system("mv {0}/{1} {0}/{2}".format(self.save_path, filename, newname))
        except Exception as e:
            raise DatabaseError("Failed to rename file: {}".format(e))

    def delete_save(self, filename):
        """ Remove an old stored file """
        if not filename:
            return
        try:
            system('rm {}/{}'.format(self.save_path, filename))
        except Exception as e:
            raise DatabaseError("Failed to delete file: {}".format(e))


class Database:
    """
    Wrapper class to handle a connection to a database
    May be created on its own - intended for use on remove device writing data
    """
    def __init__(self, ip, port, password):
        self.ip = ip  # ip of database
        self.port = port  # database port
        self.password = password  # database password

        # Separate redis pools for reading decoded data or reading raw bytes data.
        # not sure how to give Redis instances to certain sessions.
        self.pool = redis.ConnectionPool(host=ip, port=port, password=password, decode_responses=True)
        self.bytes_pool = redis.ConnectionPool(host=ip, port=port, password=password, decode_responses=False)
        self.redis = redis.Redis(connection_pool=self.pool)
        self.bytes_redis = redis.Redis(connection_pool=self.bytes_pool)

        self.exit = False  # flag to determine when to stop running if looping
        self.live = False   # Whether in live mode
        self.playback_speed = 1  # speed multiplier in playback mode (live mode False)

        # For different threads to keep track of their own last read operation point.
        # First level keys are the ID of each separate reader. Values are second level dictionaries.
        # Second level keys are the ID of each stream in the database. Values are third level dictionaries.
        # Third level keys are "id" and "time", which are the last read database key and the real time it was read.
        self.bookmarks = {}

    def time_to_redis(self, unix_time):
        """ Convert unix time in seconds to a redis timestamp, which is a string of an int in milliseconds """
        return str(int(1000*unix_time))

    def redis_to_time(self, redis_time):
        """ Convert redis time stand to unix time stamp in seconds """
        return float(redis_time.split('-')[0])/100

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
            - If not None, ignores <max_time> and <reader>
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

        else:
            last_read = bookmarks.get(stream)
            if last_read:  # last read spot exists
                last_read_id = last_read['id']
                last_read_time = last_read['time']
                time_since = time()-last_read_time  # time since last read
                if max_time and time_since > max_time:
                    # if time since last read is greater than set maximum,
                    # increment last read ID by the difference
                    new_id = self.redis_to_time(last_read_id) + (time_since-max_time)
                    last_read_id = self.time_to_redis(new_id)  # convert back to redis timestamp

                if self.live:  # read from last ID to now
                    response = red.xread({'stream:' + stream: last_read_id})
                else:  # read from last ID to ID given by time_since
                    new_id = self.redis_to_time(last_read_id) + time_since
                    max_read_id = self.time_to_redis(new_id)
                    response = red.xrange('stream:'+stream, min=last_read_id, max=max_read_id)

            else:  # no last read spot
                if self.live:  # start reading from latest, block for 1 sec
                    response = red.xread({'stream:'+stream: '$'}, block=1000)
                else:  # return nothing and set info for next read
                    # set last read id to minimum, set last read time to now
                    self.bookmarks[reader][stream] = {'id': self.time_to_redis(0), 'time': time()}
                    response = None

        if not response:
            return None

        if not self.bookmarks[reader].get(stream):
            self.bookmarks[reader][stream] = {}

        # set last read time
        self.bookmarks[reader][stream]['time'] = time()

        # store the last ID of this stream and get list of data dicts
        if count:
            self.bookmarks[reader][stream]['id'] = response[-1][0]
            data_list = response
        else:
            self.bookmarks[reader][stream]['id'] = response[0][1][-1][0]
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
    def read_snapshot(self, stream, reader, to_json=False, decode=True):
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

        if self.live:  # read most recent snapshot regardless of reader
            response = red.xrevrange('stream:'+stream, count=1)

        else:  # read snapshot at time since last read
            bookmarks = self.bookmarks.get(reader)  # get reader-specific bookmarks
            if not bookmarks:  # this reader hasn't read before
                bookmarks = {}
                self.bookmarks[reader] = bookmarks

            last_read = bookmarks.get(stream)
            if last_read:  # last read spot exists
                last_read_id = last_read['id']
                last_read_time = last_read['time']
                time_since = time()-last_read_time  # time since last read
                new_id = self.redis_to_time(last_read_id) + time_since
                max_read_id = self.time_to_redis(new_id)
                response = red.xrevrange('stream:'+stream, max=max_read_id, count=1)
            else:  # no first read spot exists
                response = red.xrange('stream:'+stream, count=1)  # get the first one
                self.bookmarks[reader][stream] = {'id': self.time_to_redis(0), 'time': time()}

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


class ServerDatabase(Database):
    """
    Wrapper class to handle a connection to a database on the server where the database is hostred
    Shouldn't be created directly - created only by DatabaseController.new()
    """
    def __init__(self, ip, port, password, file, save_path, live):
        super().__init__(ip, port, password)
        self.live = live
        self.file = file  # main database file to read from
        self.save_path = save_path  # path to save directory

    def save(self, filename=None, shutdown=False):
        """
        Save the current database to disk
        <save> whether to save the file in the storage directory,
            and returns the full filename used (may not be the same as given)
        """
        if not self.live:
            raise DatabaseError("Did not save database file - not a live database")
        if not self.redis:
            if not self.connect(timeout=5):
                raise DatabaseError("Did not save database file - could not connect to Redis Server")

        self.redis.save()  # save database to current dump file
        if not path.isfile(self.file):
            raise DatabaseError("Failed to save database file - no database file was found")

        # if file name not given or already exists
        if not filename or path.isfile(self.save_path + '/' + filename):
            filename = get_time_filename()
        if not filename.endswith('.rdb'):
            filename += '.rdb'

        try:  # move current dump file to 'saved' directory with new name
            system("cp {} {}/{}".format(self.file, self.save_path, filename))
        except Exception as e:
            raise DatabaseError("Failed to save database file to '{}': {}".format(filename, e))

        try:  # clear contents of live dump file
            self.redis.flushdb()
        except Exception as e:
            raise DatabaseError("Failed to flush database file '{}': {}".format(filename, e))

        if shutdown:
            try:
                self.redis.shutdown()
            except Exception as e:
                raise DatabaseError("Failed to shut down database: {}".format(e))

        return filename








