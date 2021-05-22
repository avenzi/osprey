from threading import Thread, current_thread
from multiprocessing import Process, current_process, Pipe, Lock, Condition
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
import numpy as np
import traceback
import time
import os


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
        self.encoding = 'iso-8859-1'  # encoding for all data main (latin-1)

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
            self.display("[{}][{}][{}]: {}".format(self.get_time(), current_process().name, current_thread().name, msg), False, True)

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
        self.device = node.device

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
            self.debug("Pipe interrupted: '{}'".format(self.name))
        except EOFError:  # connection closed
            self.debug("EOF: Pipe '{}' closed".format(self.name))
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
    Base class for Connection Nodes.
    Holds an index of IPC pipes to other Nodes.
    """
    def __init__(self, name=None, device='Unnamed_Device'):
        super().__init__()
        if not name:
            name = self.__class__.__name__
        self.name = name
        self.device = device
        self.id = self.generate_uuid()  # unique id

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


class HostNode(Node):
    """
    The main hosting connection (a Server or Client).
    Run on the main process.
    Worker connections are started on new processed and communicated with using pipes.
    <auto> Boolean: whether to automatically shutdown when all worker nodes have shutdown.
    """
    def __init__(self, name, auto=True):
        super().__init__(name=name, device=name)  # node name is the device name for the host
        self.automatic_shutdown = auto
        self.pipes = {}   # index of Pipe objects, each connecting to a WorkerConnection

    def run(self):
        """
        Default main entry point. Can be overwritten.
        Must be called on the main thread of a process.
        Blocks until exit status set.
        """
        Thread(target=self._run, name=self.name+'-RUN', daemon=True).start()
        self.run_exit_trigger(block=True)  # block main thread until exit

    def _run(self):
        """
        Called by run() on a new thread.
        Performs main execution cycle of the derived host object.
        """
        pass

    def idle(self):
        """
        Optional default action when all workers are terminated and automatic_shutdown is not set.
        Called on a new thread.
        """
        pass

    def run_worker(self, worker):
        """
        Start the given worker node on a new process.
        Adds the new Pipe to the pipe index, and starts reading from it on a new thread.
        """
        # multiprocessing duplex connections (doesn't matter which end of the pipe is which)
        host_conn, worker_conn = Pipe()

        # worker knows the host name but not the host process
        worker_pipe = PipeHandler(self, host_conn)

        # process for new worker
        worker_process = Process(target=worker.run, args=(worker_pipe,), name=worker.name, daemon=True)

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
            if self.automatic_shutdown:  # shutdown because no workers left
                self.debug("No workers left - shutting down '{}'".format(self.name))
                self.shutdown()
            else:  # put in idle mode because no workers left
                Thread(target=self.idle, name=self.name+'-IDLE', daemon=True).start()

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
        super().cleanup()  # shutdown all sockets
        for pipe in list(self.pipes.values()):  # force as iterator because items are removed from the dictionary
            pipe.send('SHUTDOWN')  # signal all workers to shutdown
            pipe.terminate()  # terminate the process if not already
        self.debug("All worker nodes terminated on Host '{}'".format(self.name), 1)


class WorkerNode(Node):
    """
    Delegated tasks by a host node, run on it's own process.
    self.name is the name of the Handler handling this node
    self.device is the device sending the stream.
    """
    def __init__(self, device=None):
        super().__init__(device=device)
        self.pipe = None  # Pipe object to the HostNode

    def run(self, pipe):
        """
        Main entry point.
        Run this Worker on a new process.
        pipe must be a PipeHandler leading to the host node.
        Should be run on it's own Process's Main Thread
        """
        self.pipe = pipe
        self.log("RUNNING")
        #self.debug("Worker '{}' started running on '{}'".format(self.name, self.device), 1)
        Thread(target=self._run, name='RUN', daemon=True).start()
        Thread(target=self._run_pipe, name='PIPE', daemon=True).start()
        self.run_exit_trigger(block=True)  # Wait for exit status on new thread

    def _run(self):
        """ Starts running all sockets, if any. """
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
        super().cleanup()
        self.debug("{} from {} Closed.".format(self.name, self.device))
        self.pipe.send('SHUTDOWN')  # Signal to the server that this connection is shutting down


# misc
class MovingAverage:
    """
    Keeps a moving average using a ring buffer
    <size> Size of the moving average buffer
    """
    def __init__(self, size):
        self.size = size  # max size
        self.length = 0  # current size

        self.array = []  # value array
        self.head = 0  # next index at which to place a value

        self.value = 0  # current average

    def calculate(self):
        """ calculate the current average """
        self.value = np.average(self.array)

    def add(self, val):
        """ Add a value to the moving average """
        if self.length < self.size:  # not full
            self.array.append(val)
            self.length += 1
        else:  # full
            self.array[self.head] = val
        self.head = (self.head + 1) % self.size
        self.calculate()
        return self.value


def validate_input(message, expecting, case=False):
    """
    Wrapper to validate input from a user
    <message> input message to be displayed
    <expecting> List of expected strings
    <case> Bool, whether case sensitive. If False, answer is always converted to lower case.
    """
    # TODO: add regex option to the <expecting> argument
    if not case:  # not case sensitive
        expecting = [s.lower() for s in expecting]

    while True:
        ans = input(message).strip()
        if not case:
            ans = ans.lower()
        if ans in expecting:  # valid
            break
        else:  # invalid
            print("Invalid input. Expecting: {}".format(expecting))

    return ans
