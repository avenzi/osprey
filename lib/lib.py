from multiprocessing import Process, current_process, Pipe, Lock, Condition, Event
from threading import Thread, current_thread

from datetime import datetime
import functools
from uuid import uuid4
import json
import traceback
import time
import os

import socketio

from lib.database import Database


class Base:
    """
    Base class from which all others inherit.
    Implements global logging functionality.
    """
    debug_level = 0  # debugging level
    log_file = None  # logging file path
    log_lock = Lock()  # lock on output

    def __init__(self):
        self.exit = False  # status flag  determine when the class should stop running
        self.close = False  # status flag to determine when the class should completely shutdown
        self.exit_condition = Condition()  # condition lock to stop running
        self.shutdown_condition = Condition()  # condition lock block until everything is completely shutdown

    def run_exit_trigger(self, block=False):
        """
        Runs exit trigger.
        If non-blocking, the exit trigger runs on a new thread (KeyboardInterrupts will be ignored)
        If blocking, the exit trigger runs on the current thread. If run on the MainThread,
            KeyboardInterrupts will be caught. Otherwise, they will be ignored.
        """
        if not block:  # run exit trigger on separate thread
            Thread(target=self._exit_trigger, name='CLEANUP', daemon=True).start()
        else:  # run exit trigger on current thread
            self._exit_trigger()

    def _exit_trigger(self):
        """
        Waits until exit status is set.
        When triggered, calls cleanup if close status is set
        """
        try:
            with self.exit_condition:
                self.exit_condition.wait()  # wait until notified
        except KeyboardInterrupt:
            if current_process().name == 'MainProcess':
                self.log("Manual Termination")  # only display once

        except Exception as e:
            self.debug("Unexpected exception in exit trigger of '{}': {}".format(self.__class__.__name__, e))
        finally:
            if self.close:  # if close flag is set
                self.cleanup()
            with self.shutdown_condition:
                self.shutdown_condition.notify_all()  # notify that cleanup has finished

    def set_debug(self, level):
        Base.debug_level = level

    def set_log_path(self, path):
        """
        Sets the path to the logging file and the logging mode
        <path> is the path to the logging directory which will contain the log file
        """
        if not os.path.isdir(path):
            os.mkdir(path)
        Base.log_file = os.path.join(path, "log.log")

        # erase contents of old log file
        # TODO: maybe keep the ~5 most recent log files?
        #  will need to change similar truncating code in LogHandler INIT
        try:
            with open(Base.log_file) as file:
                file.truncate(0)
        except:
            pass

    def get_date(self):
        """ Return the current date and time in HTTP Date-header format """
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    def get_time(self):
        """ Return the current time for debugging purposes """
        return datetime.now().strftime("%-H:%-M:%-S:%f")

    def display(self, msg, console=True, file=True, newline=True):
        """
        display a log message
        <console> whether to send to stdout
        <file> whether to log in the log file
        """
        if newline:
            end = '\n'
        else:
            end = ''
        try:
            with Base.log_lock:  # get exclusive lock on outputs
                if console:
                    print(msg, end=end)  # display on console
                if file and Base.log_file:
                    with open(Base.log_file, 'a') as file:  # write to log file
                        file.write(msg+'\n')
        except:
            return

    def log(self, message, newline=True):
        """ Outputs a log message """
        self.display("> {}".format(message), newline=newline)

    def debug(self, msg, level=1):
        """ Sends a debug level message """
        if Base.debug_level >= level:
            self.display("[{}]: {}".format(self.get_time(), msg))

    def throw(self, msg, cause=None, trace=True):
        """ display error message and halt """
        self.shutdown()  # set both exit and shustdown flags
        err = "Process: {}\nThread: {}\nERROR: {}\n".format(current_process().name, current_thread().name, msg)
        if cause is not None:
            err += "CAUSE: {}\n".format(cause)
        self.display(err)
        if trace:
            with Base.log_lock:
                traceback.print_exc()

    def generate_uuid(self):
        """ Return a UUID as a URN string """
        return uuid4().urn[9:]

    def halt(self):
        """ Set only the exit flag and exit """
        self.exit = True  # signal to stop running
        with self.exit_condition:
            self.exit_condition.notify_all()  # notify waiting thread

    def shutdown(self, block=False):
        """
        set both the exit flag and shutdown flag.
        If block is True, waits for shutdown to complete.
        """
        if self.close and self.exit:  # shutdown already called
            return
        self.halt()
        self.close = True
        if block:
            with self.shutdown_condition:
                self.shutdown_condition.wait()  # wait until cleanup is finished

    def cleanup(self):
        """
        Should not be called directly.
        Should be overwritten to do anything that should happen before terminating.
        This method is called in _exit_trigger.
        """
        pass


class PipeHandler(Base):
    """
    An object representing a tunnel to a Node object running in another process
    <name> Name of the Connection
    <conn> Connection object returned by multiprocessing.Pipe()
    <process> Process that is running on the other end of the pipe
    """
    def __init__(self, node, conn, process=None):
        super().__init__()
        self.name = node.name
        self.pipe = conn
        self.process = process

    def send(self, payload):
        """ Send a message through the process pipe """
        try:
            self.pipe.send(payload)
        except:
            self.debug("Unable to send message through pipe {}".format(self.name), 2)

    def receive(self):
        """ Wait for then return a message from the pipe queue """
        try:
            return self.pipe.recv()
        except KeyboardInterrupt:
            self.debug("Pipe interrupted: '{}'".format(self.name), 2)
        except EOFError:  # connection closed
            self.debug("EOF: Pipe '{}' closed".format(self.name), 2)
        except Exception as e:
            self.debug("Failed to read from pipe '{}': {}".format(self.name, e), 2)

    def terminate(self):
        """ Terminate the process after a shutdown window """
        if not self.process:  # is a worker pipe
            return
        if not self.process.is_alive():  # if already terminated
            return
        self.process.join(0.1)  # allow process time to shutdown
        time.sleep(0.1)  # give the process time to register as terminated
        if self.process.is_alive():  # if the process is still alive
            self.process.terminate()  # forcibly terminate it
            self.debug("Manually Terminated Process '{}'".format(self.name), 2)

    def close(self):
        """ Closes the connection """
        self.pipe.close()


class Node(Base):
    """
    Old class that was used to run threading pools
    """
    def __init__(self, name=None):
        super().__init__()
        if not name:
            name = self.__class__.__name__
        self.name = name

        from concurrent.futures import ThreadPoolExecutor

        # Thread pool used by all sockets on this node
        # default number of threads 5*core count
        self.pool = ThreadPoolExecutor(thread_name_prefix=self.name)

    def example_handle_function(self, func, threaded=True):
        """ An example method from when a threading pool was used to run threaded commands on a node """
        if self.exit or self.close:  # shutting down, don't handle more
            return
        try:

            if threaded:  # run command in thread pool
                self.pool.submit(func)
            else:  # run command synchronously
                func()
        except Exception as e:
            self.throw("Error running function", e)

    def cleanup(self):
        """ Terminate all running threads in the pool """
        self.pool.shutdown()  # shutdown thread pool
        self.debug("All Sockets shut down on Node '{}'".format(self.name))


class Client(Base):
    """
    The master Node, which delegates Streamer nodes to different processes
    Run on the main process.
    Worker connections are started on new processed and communicated with using pipes.
    <workers> list of worker classes to run
    <config> path to config file
    """
    def __init__(self, workers, name, server_ip, port, db_port, db_pass, debug=0):
        super().__init__()
        self.workers = workers
        self.name = name
        self.ip = server_ip
        self.port = port
        self.db_port = db_port
        self.db_pass = db_pass
        self.set_debug(debug)
        self.pipes = {}   # index of Pipe objects, each connecting to a WorkerNode

    def run(self):
        """
        Default main entry point. Can be overwritten.
        Must be called on the main thread of a process.
        Blocks until exit status set.
        """
        for worker in self.workers:
            worker.set_info(self)  # give worker some of the config params
            self.run_worker(worker)  # run on a parallel process

        self.log("All workers initialized.")

        # block main thread until exit
        self.run_exit_trigger(block=True)

    def run_worker(self, worker):
        """
        Runs the given worker class on a new process.
        Adds the new Pipe to the pipe index, and starts reading from it on a new thread.
        """
        # multiprocessing duplex connections (doesn't matter which end of the pipe is which)
        host_conn, worker_conn = Pipe()

        # worker knows the host name but not the host process
        worker_pipe = PipeHandler(self, host_conn)

        # process for new worker
        worker_process = Process(target=worker.run, args=(worker_pipe,), name=worker, daemon=True)

        # host knows worker name and process. Pipe is indexed by the worker ID
        self.pipes[worker.id] = PipeHandler(worker, worker_conn, worker_process)

        # new thread to act as main thread for the worker process
        Thread(target=worker_process.start, name='WorkerMainThread', daemon=True).start()

        # read from this pipe on a new thread
        Thread(target=self._run_pipe, args=(worker.id,), name=self.name+'-PIPE', daemon=True).start()

    def remove_worker(self, pipe_id):
        """
        Removes a worker pipe from the index
        Note that this does not terminate the worker process
        """
        pipe = self.pipes.get(pipe_id)
        if not pipe:  # ID not found in index
            self.debug("Host Failed to remove worker Node '{}'. Not found in worker dictionary. \
                This could be caused by a worker sending two SHUTDOWN signals.".format(pipe.name))
            return
        del self.pipes[pipe_id]  # remove from index
        if not self.pipes:  # all workers have disconnected
            self.debug("No workers left - shutting down '{}'".format(self.name))
            self.shutdown()

    def _run_pipe(self, pipe_id):
        """
        Continually waits for messages coming from the pipe.
        Handles the message by calling other methods.
        Should be run on it's own thread.
        """
        pipe = self.pipes[pipe_id]
        while not self.exit:
            message = pipe.receive()  # blocks until a message is received

            # Handle the message
            if message == 'SHUTDOWN':  # the connection on the other end shut down
                #self.debug("Host '{}' received SHUTDOWN from worker '{}'".format(self.name, pipe.name), 2)
                self.remove_worker(pipe_id)  # remove it
                return
            elif message is None:
                #self.debug("Pipe to '{}' shut down unexpectedly on node '{}'".format(pipe.name, self.name), 2)
                return
            else:
                self.debug("Host Node Received unknown signal '{}' from Worker Node '{}'".format(message, pipe.name))

    def cleanup(self):
        """ End all worker process and sockets """
        for pipe in list(self.pipes.values()):  # force as iterator because items are removed from the dictionary
            pipe.send('SHUTDOWN')  # signal all workers to shutdown
            pipe.terminate()  # terminate the process if not already
        self.debug("All worker nodes terminated on Host '{}'".format(self.name), 1)


class WorkerNode(Base):
    """
    Delegated tasks by a host node, run on it's own process.
    self.name is the name of the Handler handling this node
    self.device is the device sending the stream.
    """
    def __init__(self):
        super().__init__()
        self.name = self.__class__.__name__
        self.pipe = None  # Pipe object to the HostNode
        self.id = self.generate_uuid()

    def __repr__(self):
        return "[{}]".format(self.name)

    def run(self, pipe):
        """
        Main entry point.
        Run this Worker on a new thread.
        pipe must be a PipeHandler leading to the host node.
        Should be run on it's own Process's Main Thread.
        """
        self.pipe = pipe
        self.debug("{} initialized".format(self), 2)
        Thread(target=self._run, name='RUN', daemon=True).start()
        Thread(target=self._run_pipe, name='PIPE', daemon=True).start()
        self.run_exit_trigger(block=True)  # Wait for exit status on new thread

    def _run(self):
        """ Starts running main event loop """
        pass

    def _run_pipe(self):
        """
        Continually waits for messages coming from the pipe.
        Handles the message by calling other methods.
        Should be run on it's own thread.
        """
        # Listen for messages on the hose pipe
        while not self.exit:
            message = self.pipe.receive()  # blocks until a message is received
            # Handle the message
            if message == 'SHUTDOWN':  # Host Node signalled to shut down
                #self.debug("Worker '{}' received SHUTDOWN from Host '{}'".format(self.name, self.pipe.name), 2)
                self.shutdown()
                return
            elif message is None:
                #self.debug("Pipe to '{}' shut down unexpectedly on node '{}'".format(self.pipe.name, self.name), 2)
                return
            else:
                self.throw("Worker Node received unknown signal '{}' from Host Node '{}'. This really shouldn't have happened.".format(message, self.pipe.name))

    def cleanup(self):
        """ Shutdown all handlers associated with this connection and signal that it shut down """
        self.debug("Worker {} Closed.".format(self))
        self.pipe.send('SHUTDOWN')  # Signal to the server that this connection is shutting down


class Streamer(WorkerNode):
    """
    Used to interface with a local or remote Redis database and server socketIO
    """
    def __init__(self, name, group):
        super().__init__()
        self.name = name    # unique name within the group
        self.group = group  # unique group name that this stream is a part of

        # config settings
        self.client = None  # name of client that is hosting this worker
        self.ip = None
        self.port = None
        self.db_port = None
        self.db_pass = None

        # connection with socketio
        self.socket = socketio.Client()
        self.namespaces = ['/streamers', '/'+self.id]  # list of namespaces to connect to

        # connection to database
        self.database = None  # Database object
        self.info = {}  # info dict to be written to the database

        # flags and events
        self.streaming = Event()  # threading event flag set to activate stream

    def __repr__(self):
        return "[{}:{}]".format(self.group, self.name)

    def set_info(self, parent):
        """ Takes some parameters from the parent CLient class and sets the worker's info dict """
        self.client = parent.name
        self.ip = parent.ip
        self.port = parent.port
        self.db_port = parent.db_port
        self.db_pass = parent.db_pass

        # info dict (info sent to database)
        self.info['id'] = self.id
        self.info['name'] = self.name
        self.info['group'] = self.group
        self.info['client'] = self.client
        self.info['updated'] = 0  # last update time

    def _run(self):
        """ Runs main execution loop """
        self.init()  # initialize all connections
        self.update()  # send info to database
        self.socket.emit('init', self.id, namespace='/streamers')  # notify server

        # start loop immediately if database is ready
        if self.database.is_ready():
            self._start()

        while not self.exit:  # run until exit
            self.streaming.wait()  # block until streaming event is set
            try:
                self.loop()  # call user-defined main execution
            except Exception as e:
                self.throw("Unhandled exception: {}".format(e), trace=True)
                return

    def loop(self):
        """
        Should be overwritten by derived class.
        Should not be called anywhere other than _loop()
        """
        pass

    def register_namespace(self, NamespaceClass, namespace):
        """ Register a socketio namespace """
        self.socket.register_namespace(NamespaceClass(self, namespace))

    def connect_socket(self):
        """
        Attempt to get socketIO connection.
        Loop indefinitely if unsuccessful.
        Interestingly, it appears that if the socketIO gets disconnected and even triggers
            on_disconnect, the Client still considers it connected and any attempts to call
            connect() again will fail with the error "Already Connected." When the server
            socketIO is available again, it will reconnect automatically.
        """
        while not self.exit:
            try:
                self.socket.connect('http://{}:{}'.format(self.ip, self.port))
                self.debug("{} Connected to server socketIO".format(self))
                return True
            except Exception as e:
                #self.debug("{} failed to connect to server socketIO: {}".format(self, e))
                pass
            time.sleep(1)

    def init(self):
        """ Initialize connections """
        # register each namespace
        for namespace in self.namespaces:
            self.register_namespace(StreamerNamespace, namespace)

        # get connection to server socketIO
        self.connect_socket()

        # get connection to database
        self.database = Database(self.ip, self.db_port, self.db_pass)
        self.database.connect()
        self.log("{} Connected to Database".format(self))

    def update(self):
        """ Send info to database and signal update to server """
        # add name and ID to group column if not already
        self.database.write_group(self.group, {self.name: self.id, 'name': self.group})

        # write stream info
        self.info['updated'] = time.time()
        self.database.write_info(self.id, self.info)

        # notify server of update
        self.socket.emit('update', self.id, namespace='/streamers')

    def _start(self):
        """
        Should be extended in streamers.py
        Begins the stream
        """
        if self.streaming.is_set():  # already running
            return
        try:
            print("{} TRYING TO START".format(self))
            self.start()  # call subclassed start method
        except Exception as e:
            self.log("Failed to start {} ({})".format(self, e))
            return
        print("{} STARTED SUCCESS".format(self))
        self.streaming.set()  # set streaming, which starts the main execution while loop
        self.log("Started {}".format(self))
        self.socket.emit('log', "Started {}".format(self), namespace='/streamers')
        self.update()

    def start(self):
        """
        overwritten in subclasses
        Should only be called in _start(). Nowhere else.
        """
        pass

    def _stop(self):
        """
        Should be extended in streamers.py
        Ends the streaming process
        """
        if not self.streaming.is_set():  # already stopped
            return
        self.streaming.clear()  # stop streaming, stopping the main execution while loop
        self.stop()  # call subclassed stop method
        self.log("Stopped {}".format(self))
        self.socket.emit('log', "Stopped Streamer {}".format(self), namespace='/streamers')
        self.update()

    def stop(self):
        """
        overwritten in subclass.
        Should only be called in _stop(). Nowhere else.
        """
        pass

    def json(self, dic):
        """ To be called in response to the socketio receiving json (dict) data """
        self.log("{} Received JSON: {}".format(self.name, dic))
        pass


class Analyzer(Streamer):
    """
    Used to interface with a local or remote Redis database and server socketIO.
    Meant to read data form the database, perform some transformation on the data,
        and dump the result back into the database in a new stream.
    """

    def __init__(self, name, group):
        super().__init__(name, group)

        # index of group and names to map info of targeted streams (ID and update time)
        # {group1: {name1:{id:id, updated:time}, name2:{id:id, updated:time}, ...}, group2: {}, ...}
        self.targets = {}

        # event to control when the analyzer is waiting for the incoming stream
        self.looking = Event()

        # add namespace unique to analyzers
        self.namespaces.append('/analyzers')

    def init(self):
        """ Extend init to look for the target stream """
        super().init()
        self.get_target()  # check for target stream

    def target(self, name, group=None):
        """ Add a streamer to target with this analyzer """
        if group is None:  # same as own group
            group = self.group
        if not self.targets.get(group):
            self.targets[group] = {}
        self.targets[group][name] = {'id': None, 'updated': 0}

    def get_target(self, stream_id=None):
        """
        Check if given stream is one of the targeted streams. If it is, copy it's info.
        If no stream ID is given, look through all info dicts currently on the database.
        """
        if not stream_id:
            try:
                info_list = self.database.read_all_info()
                if not info_list:
                    raise Exception("Database Read operation returned nothing.")
            except Exception as e:
                self.debug("{} failed to get target info from database: {}".format(self, e))
                return
        else:  # stream ID given
            info_list = [self.database.read_info(stream_id)]

        info_updated = False  # flag for displaying debug info
        for info in info_list:
            group = info['group']
            name = info['name']

            if not self.targets.get(group):  # group not found
                continue
            if not self.targets[group].get(name):  # name not found in group
                continue

            # found stream not the first and not the most recently updated.
            # This only happens if there is more than 1 stream with the same name and group,
            #  which means it's an old version of the same stream.
            if float(info['updated']) < self.targets[group][name].get('updated', 0):
                continue

            # copy info from database to appropriate dictionary
            for key, val in info.items():
                try:  # attempt to convert to float
                    self.targets[group][name][key] = float(val)
                except:
                    self.targets[group][name][key] = val
            info_updated = True

        # output notification that targets were found
        if info_updated:
            for group_name, group in self.targets.items():
                for stream_name, info in group.items():
                    if info.get('id'):
                        self.debug("{} targeting [{}:{}]".format(self, group_name, stream_name))

    def _start(self):
        """ Checks for any target streams before running """
        groups = self.targets.values()
        streams = []
        for group in groups:
            for stream in group.values():
                streams.append(stream.get('id'))

        if any(streams):  # any of the target streams is present
            super()._start()
        else:
            self.log("{} not started - did not find any target streams.".format(self))


class Namespace(socketio.ClientNamespace):
    """ All methods must begin with prefix "on_" followed by socketIO message name"""
    def __init__(self, streamer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = streamer

    def on_connect(self):
        self.emit('log', '{} connected to server'.format(self.streamer))

    def on_disconnect(self):
        #self.streamer.log("{} disconnected from socketIO server".format(self.streamer.name))
        pass


class StreamerNamespace(Namespace):
    def on_update(self):
        """ Update message from server """
        self.streamer.update()

    def on_check_database(self, stream_id):
        """ Used to notify analyzers that a new stream has been initialized on the database """
        self.streamer.get_target(stream_id)

    def on_start(self):
        """ start message from server """
        self.streamer._start()

    def on_stop(self):
        """ stop message from server """
        self.streamer._stop()

    def on_json(self, dic):
        self.streamer.json(dic)


