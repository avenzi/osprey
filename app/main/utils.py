from flask import current_app, session, request
from werkzeug.utils import secure_filename

from re import match
import math
from functools import wraps
from traceback import print_exc, format_exception
from time import sleep, time, strftime, localtime

from os import listdir, system
from os.path import isfile, join

from app.main import socketio
from lib.database import DatabaseError, DatabaseTimeoutError, DatabaseBusyLoadingError, DatabaseConnectionError

# todo: make the logs in the browser reflect an actual log file on the server, and add the ability to download it.
LOG_FILE = 'local/logs/server.log'

def log(msg, level=0, everywhere=False):
    """
    Log a message in the browser.
    Level: 0=log, 1=info, 2=warn, 3=error
    If everywhere is True, broadcast to ALL browsers, even in different sessions.
    """
    msg = str(msg)  # if an exception, convert to string

    t = strftime("[%a %b %m %H:%M:%S]", localtime())
    if level == 0:
        pre = ""
    elif level == 1:
        pre = "[INFO]"
    elif level == 2:
        pre = "[WARN]"
    else:
        pre = "[ERROR]"

    # print warnings and errors to stdout
    if level >= 2:
        print("{}{}: {}".format(t, pre, msg))

    # write to log file
    with open(LOG_FILE, 'a') as file:
        file.write("{}{}: {}\n".format(t, pre, msg))

    try:
        # package log message and level to send to browser
        data = {'level': level, 'message': msg}
        if everywhere:
            socketio.emit('log', data, namespace='/browser')
        else:
            socketio.emit('log', data, namespace='/browser', room=request.sid)
    except:
        pass


def info(msg, everywhere=False):
    """ Log an info message in the browser """
    log(msg, level=1, everywhere=everywhere)  # log level 1


def warn(msg, everywhere=False):
    """ Log a warning message in the browser """
    log(msg, level=2, everywhere=everywhere)  # log level 2


def error(msg, everywhere=False):
    """ Log an error message in the browser """
    log(msg, level=3, everywhere=everywhere)  # log level 3


def catch_errors(handler):
    """ Decorator to catch and send error messages to the browser """
    @wraps(handler)
    def wrapped_handler(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except DatabaseBusyLoadingError:
            error("Database is still loading into memory - try again in a bit")
        except DatabaseTimeoutError:
            error("Database operation timed out - try again in a bit")
        except DatabaseConnectionError:
            error("Lost connection to database")
        except DatabaseError as e:
            error("Database operation failed: {}".format(e))
        except Exception as e:
            error("Server error in {}(): {}: {}\n{}".format(handler.__name__, e.__class__.__name__, e, ''.join(format_exception(e))))
    return wrapped_handler


def set_database(file=None):
    """
    Sets the current session database.
    If no file is given, sets it to a live database connection.
    If a file is given, sets it to a playback database connection to that file.
    """
    sid = session.sid  # current session ID
    ctrl = current_app.database_controller

    ctrl.remove(sid)  # remove current database
    if file:
        ctrl.new_playback(file=file, ID=session.sid)
    else:
        ctrl.new_live(ID=session.sid)

    database = ctrl.get(session.sid)
    print("SET DATABASE:", database)

    return database


def get_database():
    """ Retrieves the Database object from the current session """
    database = current_app.database_controller.get(session.sid)
    return database


def remove_database():
    """ Removes current database in session """
    current_app.database_controller.remove(session.sid)


def check_filename(file):
    """ validates syntax of a file name """
    #file = secure_filename(file)  # modifies file name if unsafe
    if not match(r"^[0-9a-zA-Z_:\-.]+$", file):
        raise Exception("Invalid file name. May only contain digits, letters, underscore, hyphen, and period.")


def bytes_to_human(size):
    """
    <size> A size in number of bytes.
    Returns human readable string representation.
    """
    units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
    if size <= 0:
        order = 0
    else:
        order = int(math.log(size, 1000))

    if order > 5:  # more than 1000 PB lol
        order = 5

    quotient = size / 1000 ** order
    unit = units[order]

    if order == 0:
        return "{:.0f} {}".format(quotient, unit)
    else:
        return "{:.1f} {}".format(quotient, unit)


"""
ADTS byte structure from: https://wiki.multimedia.cx/index.php?title=ADTS
7 bytes total:
111111111111  # sync-word to identify start
0     # MPEG-4
00    # always 00
1     # no CRC
01    # MPEG-4 profile minus 1 (2 is AAC-LC)
0100  # MPEG-4 sampling frequency (44.1kHz)
0     # private bit, unused
001   # number of channels (1)
0000  # copyright stuff, ignore
0000000000000  # frame length in bytes (including the header), to be replaced dynamically
00000000000  # buffer fullness (ignored by most decoders)
00  # number of ACC frames in this ADTS packet minus 1
"""
ADTS_STRUCTURE = 0b11111111111100010101000001000000000000000000000000000000

def add_ADTS_header(data):
    """
    Adds ADTS packet headers to raw AAC audio data.
    ADTS byte structure from: https://wiki.multimedia.cx/index.php?title=ADTS
    Use ADTS_HEADER_TEMPLATE and replace the frame length.
    If trim is True: instead of throwing an exception when the data length is too big, trim it down instead.
    """
    if not data:  # if input is empty
        return ADTS_STRUCTURE.to_bytes(7, 'big')  # base structure is the exact header for an empty frame
    output = b''
    max_size = (2**13 - 1) - 7  # max byte size (13 bit int) minus 7 bytes for the header
    while data:  # while more data left that needs packaging
        segment = data[:max_size]  # slice to max size (or less)
        size = len(segment) + 7    # total size of new packet
        # insert frame size and convert to byte string of size 7
        header = (ADTS_STRUCTURE | (size << 13)).to_bytes(7, 'big')
        output += header + segment  # prepend to this segment
        data = data[max_size:]  # chop off this segment
    return output


def request_update():
    """ Sends an update request to all streamers """
    database = get_database()
    if not database:
        return  # no database connection - do nothing
    if not database.live:
        return  # database is in playback mode.

    socketio.emit('update', namespace='/streamers')

    # hopefully give enough time to let the streamers send their update to the database
    # todo: if we want to have confirmation of an update, we must check the info:updated column in redis and check the timestamp.
    #  Streamers can't send a message through socketIO because they will be received with no way
    #  to know what session to send that info to, and we don't want that info to get sent to a session with a non-live database.
    sleep(0.5)


@catch_errors
def update_pages(room=None):
    """
    Updates list of connected streams in browser.
    If room is given, send update to that room.
    If not, send to only the current request.
    """
    database = get_database()
    if not database:
        return  # no database connection - do nothing

    try:  # attempt to read list of group names
        groups = database.get_all_groups()
    except DatabaseError as e:
        error("Error retrieving streams from database: {}".format(e))
        groups = []
    if groups is None:
        error("Tried to retrieve list of pages, got None")
        return

    if not room:  # if room not given, send to room ID of current request
        room = request.sid
    socketio.emit('update_pages', groups, namespace='/browser', room=room)


@catch_errors
def update_files(room=None):
    """
    Updates list of database files in browser.
    If room is given, send update to that room.
    If not, send to only the current request.
    """
    data_path = 'data/saved'
    files = []
    for file in listdir(data_path):
        # if a valid file and doesn't start with a period (hidden files)
        if isfile(join(data_path, file)) and not file.startswith('.'):
            files.append(file)

    if not room:  # if room not given, send to room ID of current request
        room = request.sid
    socketio.emit('update_files', files, namespace='/browser', room=room)


def set_button(name, hidden=None, disabled=None, text=None):
    """
    Updates the state of a single button in the current session.
    <name>: class name of the button to be targeted.
    <hidden>: whether the button is hidden.
    <disabled>: whether the button is disabled.
    <text>: button text, if changed.
    """
    if not session.get('buttons'):
        session['buttons'] = {}
    session['buttons'][name] = {'hidden': hidden, 'disabled': disabled, 'text': text}
    session.modified = True


@catch_errors
def update_buttons(room=None):
    """
    Sends all button data stored in session.
    If room is given, send update to that room.
    If not, send to only the current request.
    """
    if not session.get('buttons'):
        session['buttons'] = {}

    if not room:  # if room not given, send to room ID of current request
        room = request.sid
    socketio.emit('update_buttons', session['buttons'], namespace='/browser', room=room)

