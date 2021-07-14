from flask import current_app, session, request

from re import match
from functools import wraps
from traceback import print_exc

from os import listdir, system
from os.path import isfile, join

from app.main import socketio
from lib.database import DatabaseError


def log(msg):
    """ Log a message in the browser """
    socketio.emit('log', msg, namespace='/browser', room=request.sid)


def error(msg):
    """ Log an error message in the browser """
    socketio.emit('error', str(msg), namespace='/browser', room=request.sid)
    print("ERROR: {}".format(str(msg)))


def catch_errors(handler):
    """ Decorator to catch and send error messages to the browser """
    @wraps(handler)
    def wrapped_handler(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except Exception as e:
            error("Server error in {}(): {}: {}".format(handler.__name__, e.__class__.__name__, e))
            print_exc()  # print stack trace
    return wrapped_handler


def set_button(name, hidden=None, disabled=None, text=None):
    """
    Updates the state of a single button in the current session
    <name>: class name of the button to be targeted
    <hidden>: whether the button is hidden
    <disabled>: whether the button is disabled
    <text>: button text, if changed.
    """
    if not session.get('buttons'):
        session['buttons'] = {}
    session['buttons'][name] = {'hidden': hidden, 'disabled': disabled, 'text': text}


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

    # set Index Header for this session
    if database.live:  # live database
        session['index_header'] = 'Connected Live Streams'
    else:  # playback database
        session['index_header'] = 'Playback: '+database.file

    print("SET DATABASE:", database)

    return database


def get_database():
    """ Retrieves the Database object from the current session """
    database = current_app.database_controller.get(session.sid)
    print("RETRIEVED DATABASE FOR THIS SESSION:", database)
    return database


def remove_database():
    """ Removes current database in session """
    current_app.database_controller.remove(session.sid)


def check_filename(file):
    """ validated syntax of file name """
    if not match(r"^[0-9a-zA-Z_:\-.]+$", file):
        raise Exception("Invalid file name. May only contain digits, letters, underscore, hyphen, and period.")


@catch_errors
def update_pages():
    """ Updates list of connected streams in browser """
    database = get_database()
    if database:
        try:  # attempt to read list of group names
            groups = database.read_all_groups()
        except DatabaseError as e:
            error("Error retrieving streams from database: {}".format(e))
            groups = []
    else:
        error("Cannot get stream pages - No current database is set")
        return
    if groups is None:
        error("Tried to retrieve list of pages, got None")
        return
    socketio.emit('update_pages', groups, namespace='/browser', room=request.sid)


@catch_errors
def update_files():
    """ Updates list of database files in browser """
    data_path = 'data/saved'
    files = []
    for file in listdir(data_path):
        # if a valid file and doesn't start with a period (hidden files)
        if isfile(join(data_path, file)) and not file.startswith('.'):
            files.append(file)
    socketio.emit('update_files', files, namespace='/browser', room=request.sid)


@catch_errors
def update_buttons():
    """ Sends all button data stored in session """
    if not session.get('buttons'):
        session['buttons'] = {}
    print('BUTTONS: ', session['buttons'])
    session['buttons'] = {}
    socketio.emit('update_buttons', session['buttons'], namespace='/browser', room=request.sid)


@catch_errors
def update_text():
    """ Sends text data to the page to update """
    socketio.emit('update_header', session['index_header'], namespace='/browser', room=request.sid)