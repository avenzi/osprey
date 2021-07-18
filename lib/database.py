from time import time, sleep, strftime, localtime
import functools
import json
from os import system, path
from traceback import print_exc

import redis
from redistimeseries.client import Client as RedisTS


class DatabaseError(Exception):
    """ invoked when the connection fails when performing a read/write operation """
    pass


class DatabaseLoading(DatabaseError):
    """
    Invoked when the database is currently loading a file into memory.
    Essentially just used with a redis.exceptions.BusyLoadingError.
    """


def get_time_filename():
    """ Return human readable time for file names """
    return strftime("%Y-%m-%d_%H:%M:%S.rdb", localtime())


def catch_connection_errors(method):
    """
    Method wrapper to catch disconnection errors.
    Turns errors into a single DatabaseError to be caught elsewhere.
    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        try:  # attempt to perform database operation
            return method(self, *args, **kwargs)
        except redis.exceptions.BusyLoadingError:
            raise DatabaseLoading("Redis is loading the database into memory. Try again later.")
        except (ConnectionResetError, ConnectionRefusedError, TimeoutError, redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, redis.exceptions.ResponseError) as e:
            raise DatabaseError("{}: {}".format(e.__class__.__name__, e))
        except Exception as e:  # other type of error
            print_exc()
            raise DatabaseError('Uncaught Error in Database ({}). {}: {}'.format(method.__name__, e.__class__.__name__, e))
    return wrapped


class DatabaseController:
    """ Handles connections to multiple different Database instances """
    def __init__(self, live_path, saved_path):
        # index of Database objects
        # keys are ID numbers for each database
        self.sessions = {}

        self.live_ip = '3.131.117.61'
        self.live_port = 5001
        self.live_path = live_path  # directory of live database dump files
        self.live_file = 'live.rdb'
        self.live_pass = 'thisisthepasswordtotheredisserver'

        # index of ports used for playback files and how many Database object connected
        self.playback_ports = {port: {'file': None, 'count': 0} for port in [7000, 7001, 7002]}
        self.playback_ip = '127.0.0.1'
        self.save_path = saved_path

    def new_live(self, ID):
        """ Creates and returns a new live Database instance for the given ID key """
        if self.sessions.get(ID):  # Database already associated
            self.remove(ID)  # remove and disconnect
        self.sessions[ID] = ServerDatabase(
            ip=self.live_ip, port=self.live_port, password=self.live_pass,
            live=True, file=self.live_file, live_path=self.live_path, save_path=self.save_path
        )

    def new_playback(self, file, ID):
        """ Creates and returns a new playback Database instance for the given ID key """
        # iterate through index of ports
        port = None
        for p, info in self.playback_ports.items():
            if not info['file']:  # this port is available
                port = p
            elif info['file'] == file:  # the port is already associated with the given file
                port = p
                print("FOUND A PORT ALREADY ASSOCIATED FOR PLAYBACK: {}".format(p))
                break  # done

        else:  # no port was associated with this file already
            if port is None:  # no ports available
                raise DatabaseError("Could not create new playback server - no ports available")
            else:  # a port is available
                self.start_server(file=file, port=port)

        self.playback_ports[port]['file'] = file  # set the file for this port if not already
        self.playback_ports[port]['count'] += 1  # increment count of Database classes connecting to this port

        if self.playback_ports[port]['count'] <= 0:
            raise DatabaseError("Error creating playback database - number of redis instances for port {} was negative".format(port))

        if self.sessions.get(ID):  # Database already associated
            self.remove(ID)  # remove and disconnect

        # empty password
        self.sessions[ID] = ServerDatabase(
            ip=self.playback_ip, port=port, password='',
            file=file, live=False, live_path=self.live_path, save_path=self.save_path
        )

        count = self.playback_ports[port]['count']

    def get(self, ID):
        """ Get database by ID """
        return self.sessions.get(ID)

    def remove(self, ID):
        """ Disconnect a Database class and remove it from the dictionary """
        if self.sessions.get(ID):
            db = self.sessions[ID]

            # live database
            if db.live:
                return

            # playback database
            info = self.playback_ports[db.port]
            if not info:
                return
            if info['file'] and info['count'] > 1:  # still some left
                self.playback_ports[db.port]['count'] -= 1  # decrement

            # if a no more databases using this port
            elif info['file'] and info['count'] <= 1:
                db.shutdown()  # shut down this redis server
                self.playback_ports[db.port]['count'] = 0
                self.playback_ports[db.port]['file'] = None  # un-associate file from port

            del self.sessions[ID]  # remove from session index

    def rename_save(self, filename, newname):
        """ renames an old save file """
        if not filename:
            raise Exception("Could not rename file - no file given to rename")
        if not newname:
            newname = get_time_filename()
        if not newname.endswith('.rdb'):
            newname += '.rdb'
        if path.isfile(self.save_path + '/' + newname):
            raise Exception("Could not rename file - new file name already exists")
        if not path.isfile(self.save_path + '/' + filename):
            raise Exception("Could not rename file - file does not exist")
        try:
            system("mv {0}/{1} {0}/{2}".format(self.save_path, filename, newname))
        except Exception as e:
            raise DatabaseError("Failed to rename file: {}".format(e))

    def delete_save(self, filename):
        """ Remove an old stored file """
        if not filename:
            return
        if not path.isfile(self.save_path+'/'+filename):
            raise Exception("Could not delete file - file does not exist")
        try:
            system('rm {}/{}'.format(self.save_path, filename))
        except Exception as e:
            raise DatabaseError("Failed to delete file: {}".format(e))

    def start_server(self, file, port):
        """ Start a new local Redis server instance initialized from <file> on port <port> """
        system("redis-server --bind 127.0.0.1 --daemonize yes --dir {} --dbfilename {} --port {}".format(self.save_path, file, port))


class Database:
    """
    Wrapper class to handle a single connection to a database
    May be created on its own - intended for use on remove device writing data.
    """
    def __init__(self, ip, port, password):
        self.ip = ip  # ip of database
        self.port = port  # database port
        self.password = password  # database password

        # options for the redis.ConnectionPool
        options = {
            'host': ip,
            'port': port,
            'password': password,
            'socket_timeout': 2,
            'socket_connect_timeout': 5
        }

        # Separate redis pools for reading decoded data or reading raw bytes data.
        pool = redis.ConnectionPool(decode_responses=True, **options)
        bytes_pool = redis.ConnectionPool(decode_responses=False, **options)

        # Redis connection client
        self.redis = redis.Redis(connection_pool=pool)
        self.bytes_redis = RedisTS(connection_pool=bytes_pool)

        # Create RedisTimeSeries Client instances as well
        # (wrapper around Redis instance to implement RedisTimeSeries commands)
        self.redis_ts = RedisTS(conn=self.redis)
        self.bytes_redis_ts = RedisTS(conn=self.bytes_redis)
        # todo: figure out how to convert to using RedisTimeSeries

        self.exit = False  # flag to determine when to stop running if looping
        self.live = True   # Whether in live mode

        # Dictionary to track last read position in the database for each data column
        # First level keys are the ID of each stream in the database. Values are Second level dictionaries.
        # Second level keys are "id" and "time", which are the last read database key and the real time it was read.
        self.bookmarks = {}

        # for playback mode
        self.playback_speed = 1  # speed multiplier in playback mode (live mode False)
        self.playback_active = False       # whether this connection is actively playing back
        self.real_start_time = time()      # absolute time playback was last started
        self.relative_stop_time = time()   # time (relative to playback) that playback was last paused

    def time(self):
        """
        Live mode: Get current time.
        Playback mode: Get current playback time (affected by starting and stopping the playback).
        """
        if self.live:
            return time()
        else:
            if self.playback_active:  # playback is active
                diff = time()-self.real_start_time  # time since started
                return self.relative_stop_time + diff  # time difference after last stopped
            else:  # playback is paused
                return self.relative_stop_time  # only return the time at which it was paused

    def time_to_redis(self, unix_time):
        """ Convert unix time in seconds to a redis timestamp, which is a string of an int in milliseconds """
        return str(int(1000*unix_time))

    def redis_to_time(self, redis_time):
        """ Convert redis time stand to unix time stamp in seconds """
        return float(redis_time.split('-')[0])/1000

    def ping(self, catch_error=True):
        """ Ping database to ensure connecting is functioning """
        if catch_error:
            try:
                if self.redis.ping():
                    return True
            except:
                return False
        else:
            self.redis.ping()

    def is_streaming(self):
        """
        Live mode: Check database for "STREAMING" key.
        Playback mode: Check self.playback_active property.
        """
        if self.live:
            try:
                if self.redis.get('STREAMING'):
                    return True
            except:
                return False
            return False
        else:
            return self.playback_active

    @catch_connection_errors
    def get_total_time(self, stream):
        """ Gets the total length in time of a given stream """
        assert not self.live, "Cannot get total time of a live stream, only elapsed time."
        first_data_point = self.redis.xrange('stream:'+stream, count=1)
        last_data_point = self.redis.xrevrange('stream:'+stream, count=1)
        if first_data_point and last_data_point:
            start_time = self.redis_to_time(first_data_point[0][0])
            end_time = self.redis_to_time(last_data_point[0][0])
            diff = end_time - start_time
            return diff
        else:
            print("NO TOTAL: ".format(first_data_point, last_data_point))
            print("ID: ", stream)
            return 0

    @catch_connection_errors
    def get_elapsed_time(self, stream):
        """ Gets the current length of time that a database has been playing for """
        first_data_point = self.redis.xrange('stream:'+stream, count=1)
        if first_data_point:
            start_time = self.redis_to_time(first_data_point[0][0])
        else:
            return 0

        if self.bookmarks.get(stream):
            current_time = self.redis_to_time(self.bookmarks[stream]['id'])
        else:
            current_time = start_time  # if no bookmark for this stream yet, it's at the beginning
        return current_time - start_time

    @catch_connection_errors
    def write_data(self, stream, data):
        """
        Writes time series <data> to stream:<stream>.
        If <data> is a dictionary of items where keys are column names.
        Items must either all be iterable or all non-iterable.
        All Items (if iterable) must be of same length.
        Must include a 'time' column with unix time stamps in seconds.
        """
        if not data.get('time'):  # check for time key
            raise DatabaseError("Data input dictionary must contain a 'time' key.")

        # make sure all values are the same size
        sizes = set()
        for val in data.values():
            if hasattr(type(val), '__iter__'):  # iterable
                sizes.add(len(val))
            else:  # non-iterable
                sizes.add(None)
        if len(sizes) > 1:  # more than one size
            raise DatabaseError("Data input columns are not all the same size. Found sizes: {}".format(sizes))
        elif len(sizes) == 0:  # no data?
            raise DatabaseError("Data input contained no data columns? : {}".format(data))

        if hasattr(type(list(data.values())[0]), '__iter__'):  # if an iterable sequence of data points
            pipe = self.redis.pipeline()  # pipeline queues a series of commands at once
            length = len(list(data.values())[0])  # length of data (all must be the same)

            # add data to the Redis database one data point at a time
            #  because there isn't a mass-insert-to-stream command
            for i in range(length):
                d = {}
                for key in data.keys():
                    d[key] = data[key][i]
                time_id = self.time_to_redis(data['time'][i])  # redis time stamp in which to insert
                pipe.xadd('stream:'+stream, d, id=time_id)

            pipe.execute()
        else:  # assume this is a single data point
            self.redis.xadd('stream:'+stream, {key: data[key] for key in data.keys()}, id=data['time'])

    @catch_connection_errors
    def read_data(self, stream, count=None, max_time=None, numerical=True, to_json=False, decode=True):
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

        if stream is None:
            return

        if count:  # get COUNT data regardless of last read
            response = red.xrevrange('stream:'+stream, count=count)

        else:
            last_read = self.bookmarks.get(stream)
            if last_read:  # last read spot exists
                last_read_id = last_read['id']
                last_read_time = last_read['time']
                temptime = self.time()
                time_since = self.time()-last_read_time  # time since last read
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

                    # Redis uses the prefix "(" to represent an exclusive interval for XRANGE
                    response = red.xrange('stream:'+stream, min='('+last_read_id, max=max_read_id)
                    m = "FULLR" if response else "EMPTY"
                    print("\n------ [{}] {}. last_read_time: {}, now_time: {}, \n-----------time_since: {}, last_read_id: {}, max_id: {}".format(stream, m, last_read_time, temptime, time_since, last_read_id, max_read_id))

            else:  # no last read spot
                if self.live:  # start reading from latest, block for 1 sec
                    response = red.xread({'stream:'+stream: '$'}, block=1000)
                else:  # return nothing and set info for next read
                    # set last read id to the first time stamp available
                    # set last read time to the time that playback was started
                    first_data_point = red.xrange('stream:'+stream, count=1)
                    if first_data_point:
                        first_time_stamp = first_data_point[0][0]
                        self.bookmarks[stream] = {'id': first_time_stamp, 'time': self.time()}
                    response = None

        if not response:
            return None

        if not self.bookmarks.get(stream):
            self.bookmarks[stream] = {}

        # set last read time
        self.bookmarks[stream]['time'] = self.time()

        # store the last timestamp ID in this response

        # If count is given or in playback mode,
        #  XRANGE is used, which gives a list of dictionaries
        if count or not self.live:
            self.bookmarks[stream]['id'] = response[-1][0]  # store last timestamp
            data_list = response  # get list of data dicts

        # If count isn't given and in live mode,
        #  XREAD is used, which gives a list of tuples.
        # But since we read from only one stream,
        #  the actual data is in response[0][1].
        else:
            self.bookmarks[stream]['id'] = response[0][1][-1][0]  # store last timestamp
            data_list = response[0][1]  # get list of data dicts

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

    @catch_connection_errors
    def write_snapshot(self, stream, data):
        """
        Writes a snapshot of data <data> to stream:<stream>.
        <data> must be a dictionary of lists, where keys are data column names.
        Note that this method is for data which is not consecutive (like time series would be).
        It is for data that is meant to be viewed a chunk at a time.
        It places each list of data values as a comma separated list under one key.
        Must include a 'time' column with unix time stamps in seconds.
        """
        if not data.get('time'):  # check for time key
            raise DatabaseError("Data input dictionary must contain a 'time' key.")
        if type(data['time']) not in [int, float]:
            raise DatabaseError("Time of this snapshot must be an integer or float.")

        new_data = {}
        for key in data.keys():
            new_data[key] = ','.join(str(val) for val in data[key])

        self.redis.xadd('stream:'+stream, new_data, id=data['time'])

    @catch_connection_errors
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

        if self.live:  # read most recent snapshot
            response = red.xrevrange('stream:'+stream, count=1)

        else:  # read snapshot at time since last read
            last_read = self.bookmarks.get(stream)
            if last_read:  # last read spot exists
                last_read_id = last_read['id']
                last_read_time = last_read['time']
                time_since = self.time()-last_read_time  # time since last read
                new_id = self.redis_to_time(last_read_id) + time_since
                max_read_id = self.time_to_redis(new_id)
                response = red.xrevrange('stream:'+stream, max=max_read_id, count=1)
            else:  # no first read spot exists
                response = red.xrange('stream:'+stream, count=1)  # get the first one
                self.bookmarks[stream] = {'id': self.time_to_redis(0), 'time': self.time()}

        if not response:
            return None

        # only store bookmarks if in playback mode
        if not self.live:
            if not self.bookmarks.get(stream):
                self.bookmarks[stream] = {}

            # set last read time
            self.bookmarks[stream]['time'] = self.time()

            # store the last timestamp ID in this response
            self.bookmarks[stream]['id'] = response[-1][0]  # store last timestamp

        data = response[0][1]  # data dict
        keys = data.keys()  # get keys from data dict
        output = {key: [] for key in keys}

        for key in keys:
            vals = data[key].split(',')
            output[key] = [float(val) for val in vals]

        if to_json:
            return json.dumps(output)
        return output

    @catch_connection_errors
    def write_info(self, key, data):
        """
        Writes <data> to info:<key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('info:'+key, data)

    @catch_connection_errors
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

    @catch_connection_errors
    def read_all_info(self):
        """ Gets a list of dictionaries containing info for all connected streams """
        info = []
        for key in self.redis.execute_command('keys info:*'):
            info.append(self.redis.hgetall(key))
        return info

    @catch_connection_errors
    def write_group(self, key, data):
        """
        Writes <data> to group:<key>
        <data> must be a dictionary of key-value pairs.
        <key> is the key for this data set
        """
        self.redis.hmset('group:'+key, data)

    @catch_connection_errors
    def read_group(self, name, stream=None):
        """
        Gets an info dict from stream with name <stream> in group_name <name>
        if <name> not specified, gives list of all dicts in that group.
            - Note that this only returns one dict for each 'info:' data column,
                so any extra 'stream:' columns with the same but a different prefix
                do not add another dict.
        """
        if stream is not None:  # stream name specified
            stream_id = self.redis.hget('group:'+name, stream)  # get stream ID from group dict
            return self.read_info(stream_id)  # return dict for that stream

        else:  # no stream name specified - get whole group
            data = {}  # name: {stream info dict}
            group = self.redis.hgetall('group:'+name)  # name:ID
            for key in group.keys():  # for each stream name
                info = self.read_info(group[key])
                if info:
                    data[key] = info
            return data

    @catch_connection_errors
    def read_all_groups(self):
        """ Gets a list of dictionaries containing name and ID info for all connected streams """
        info = []
        for key in self.redis.execute_command('keys group:*'):
            info.append(self.redis.hgetall(key))
        return info

    @catch_connection_errors
    def read_streams(self, group):
        """
        Return a dictionary of all streams in a group
        This returns all 'stream:' columns in a group,
            including duplicated with different prefixes.
        """
        # todo: because I need a way to consistently find streams with prefixes,
        #       the method for creating them should be standardized and unchangeable.
        #  The best way to do this would be to hide their structure from the user.
        #  Right now, the user could technically write data to any stream name with
        #       any structure in the loop method of an Analyzer or streamer.
        #  To fix this, there should be a given method to "name" a stream, but under the hood
        #       always add the stream ID to it.
        #  The trouble then is how to retrieve that full ID in the create_layout() method.
        #  I think that whole thing should be redone - maybe as a class method that must be inherited?
        #  .
        #  For the purposes of this method, the structure is assumed to be:
        #  stream:prefix:full_stream_id
        data = {}  # name: ID
        group = self.redis.hgetall('group:'+group)  # name:ID
        for key, ID in group.items():
            # get all streams from this ID with an extra prefix
            extra_ids = self.redis.keys("stream:*{}".format(ID))
            for extra in extra_ids:
                i = extra.find(":")+1  # first colon
                j = extra[i:].find(":")  # second colon
                if j == -1:  # no second colon (thus no prefix)
                    name = key
                else:
                    name = key+':'+extra[i:i+j]
                data[name] = extra[i:]
        return data


class ServerDatabase(Database):
    """
    Wrapper class to handle a connection to a database on the server where the database is hostred
    Shouldn't be created directly - created only by DatabaseController.new()
    """
    def __init__(self, ip, port, password, file, live, live_path, save_path):
        super().__init__(ip, port, password)
        self.live = live
        self.file = file  # main database file to read from
        self.live_path = live_path  # path to live directory
        self.save_path = save_path  # path to save directory

    def __repr__(self):
        return "PORT: {}, LIVE: {}, FILE: {}".format(self.port, self.live, self.file)

    def start(self):
        """
        Live mode: Sets "STREAMING" key in database.
        Playback mode: Starts playback.
        """
        if self.live:
            self.redis.set('STREAMING', 1)  # set RUNNING key
        else:
            self.real_start_time = time()  # mark last playback start time
            self.playback_active = True

    def stop(self):
        """
        Live mode:  removes "RUNNING" key in database.
        Playback mode: Pauses playback.
        """
        if self.live:
            self.redis.delete('STREAMING')  # unset RUNNING key
        else:
            self.relative_stop_time = self.time()  # mark playback pause time relative to playback
            self.playback_active = False

    def save(self, filename=None, shutdown=False):
        """
        Save the current database to disk
        <save> whether to save the file in the storage directory,
            and returns the full filename used (may not be the same as given)
        """
        if not self.live:
            raise DatabaseError("Did not save database file - not a live database")

        self.redis.save()  # save database to current dump file

        if not path.isfile(self.live_path+'/'+self.file):
            raise DatabaseError("Failed to save database file - no database file was found")

        # if file name not given or already exists
        if not filename or path.isfile(self.save_path+'/'+filename):
            filename = get_time_filename()
        if not filename.endswith('.rdb'):
            filename += '.rdb'

        try:  # move current dump file to 'saved' directory with new name
            system("cp {}/{} {}/{}".format(self.live_path, self.file, self.save_path, filename))
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

    def shutdown(self):
        """ Shutdown the redis server instance """
        if self.live:  # if live database
            self.save(shutdown=True)  # save first
        else:  # shutdown playback database without saving
            try:
                self.redis.shutdown(save=False)
            except Exception as e:
                raise DatabaseError("Failed to shutdown database on port: {}. {}: {}".format(self.port, e.__class__.__name__, e))

    def kill(self):
        """ manually kills the redis process by stopping activity on the port it's using """
        system("sudo fuser -k {}/tcp".format(self.port))







