from flask import request, current_app, session
from time import sleep
from re import match
from functools import wraps

from os import listdir, system
from os.path import isfile, join

from app.main import socketio
from lib.database import DatabaseError


def log(msg):
    """ Log a message in the browser """
    socketio.emit('log', msg, namespace='/browser')


def error(msg):
    """ Log an error message in the browser """
    socketio.emit('error', str(msg), namespace='/browser')
    print("ERROR: {}".format(msg))


def catch_errors(handler):
    """ Decorator to catch and send error messages to the browser """
    @wraps(handler)
    def wrapped_handler(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except Exception as e:
            error(e)
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

    # set Index Header for this session
    if database.live:  # live database
        session['index_header'] = 'Connected Live Streams'
    else:  # playback database
        session['index_header'] = 'Playback: '+database.file

    return database


def get_database():
    """ Retrieves the Database object from the current session """
    database = current_app.database_controller.get(session.sid)

    # no database found for this session
    if not database:
        database = set_database()  # set database to live connection

    # set Index Header for this session
    if database.live:  # live database
        session['index_header'] = 'Connected Live Streams'
    else:  # playback database
        session['index_header'] = 'Playback: '+database.file

    return database


def remove_database():
    """ Removes current database in seesion"""
    current_app.database_controller.remove(session.sid)


def check_filename(file):
    """ validated syntax of file name """
    if not match(r"^[0-9a-zA-Z_:\-.]+$", file):
        raise Exception("Invalid file name. May only contain digits, letters, underscore, hyphen, and period.")


def update_pages():
    """ Updates list of connected streams in browser """
    try:  # attempt to read list of group names
        groups = get_database().read_all_groups()
    except DatabaseError:
        groups = []
    print("GROUPS: ", type(groups))
    socketio.emit('update_pages', groups, namespace='/browser')


def update_files():
    """ Updates list of database files in browser """
    data_path = 'data/saved'
    try:  # attempt to get list of files in data directory
        files = [file for file in listdir(data_path) if isfile(join(data_path, file))]
    except Exception as e:
        print(e)
        files = []
    socketio.emit('update_files', files, namespace='/browser')


def update_buttons():
    """ Sends all button data stored in session """
    socketio.emit('update_buttons', current_app.buttons, namespace='/browser')


def update_text():
    """ Sends text data to the page to update """
    socketio.emit('update_header', session['index_header'], namespace='/browser')


def set_button(name, hidden=None, disabled=None, text=None):
    """
    Updates state of a single button in browser
    <name>: class name of the button to be targeted
    <hidden>: whether the button is hidden
    <disabled>: whether the button is disabled
    <text>: button text, if changed.
    """
    data = {'name': name, 'hidden': hidden, 'disabled': disabled, 'text': text}
    current_app.buttons.append(data)


##################################

@socketio.on('connect', namespace='/browser')
@catch_errors
def connect():
    """ On connecting to the browser """
    print("SID CONNECT: ", session.sid)
    get_database()  # get database for session
    refresh()  # send all page info immediately on connecting


@socketio.on('disconnect', namespace='/browser')
@catch_errors
def disconnect():
    """ On disconnecting from the browser """
    pass


####################################
# Handlers for browser buttons


@socketio.on('start', namespace='/browser')
@catch_errors
def start():
    """ start all streams """
    if get_database().ping():  # make sure database connected
        if get_database().live:  # live mode
            socketio.emit('start', namespace='/streamers')  # send start command to streamers
            set_button('start', disabled=True)
            set_button('stop', disabled=False)
            update_buttons()
        else:  # playback mode
            print("PLAYBACK MODE START")
    else:
        error('Cannot start streams - database ping failed')


@socketio.on('stop', namespace='/browser')
@catch_errors
def stop():
    """ Stop streams, dump database file to disk, start a clean database file """
    socketio.emit('stop', namespace='/streamers')  # send stop command to streamers

    database = get_database()
    filename = database.save()  # save database file (if live) and wipe contents
    log('Session Saved: {}'.format(filename))

    socketio.emit('update', namespace='/streamers')  # request info update from streamers
    set_button('start', disabled=False)
    set_button('stop', disabled=True)
    sleep(0.1)
    refresh()


@socketio.on('refresh', namespace='/browser')
@catch_errors
def refresh():
    """ Refresh all data displayed in browser index """
    update_text()
    update_pages()
    update_files()
    update_buttons()


@socketio.on('playback', namespace='/browser')
@catch_errors
def playback():
    """ Switches back to playback mode for current database file """
    error("Playback button not implementec")
    #set_button('live', hidden=False, disabled=False)
    #set_button('playback', hidden=True)
    #refresh()


@socketio.on('live', namespace='/browser')
@catch_errors
def live():
    """ Switches back to current live database  """
    log('Switching to live database')
    set_button('live', hidden=True)
    #set_button('playback', hidden=False, disabled=False)
    set_database()  # set database to live
    refresh()


@socketio.on('load', namespace='/browser')
@catch_errors
def load(filename):
    """ Loads the given database file for playback """
    set_database(filename)  # set a playback database for the given file
    set_button('live', hidden=False, disabled=False, text='New Session')
    #set_button('playback', disabled=True)
    log('Loaded "{}" to database'.format(filename))
    refresh()


@socketio.on('rename', namespace='/browser')
@catch_errors
def rename(data):
    """ Renames the selected file """
    old = data['filename']
    new = data['newname']
    check_filename(old)
    check_filename(new)
    current_app.database_controller.rename_save(old, new)
    log('Renamed "{}" to "{}"'.format(old, new))
    refresh()


@socketio.on('delete', namespace='/browser')
@catch_errors
def delete(filename):
    """ Deletes the selected file """
    current_app.database_controller.delete_save(filename)
    log('Deleted file "{}"'.format(filename))
    refresh()
