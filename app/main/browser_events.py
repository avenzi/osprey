from flask import request, current_app, session
from time import sleep
from re import match
from functools import wraps

from os import listdir, system
from os.path import isfile, join

from app.main import socketio
from app import Database


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


def get_database():
    """ Retrieves the Database object from the current session """
    if not session.get('DATABASE'):
        print("SESSION VAR NOT SET")
        session['DATABASE'] = "VALUE"
    else:
        print("SESSION VAR SET")
    print(session['DATABASE'])
    return session['DATABASE']


def check_filename(file):
    """ validated syntax of file name """
    if not match(r"^[0-9a-zA-Z_:\-.]+$", file):
        raise Exception("Invalid file name. May only contain digits, letters, underscore, hyphen, and period.")


def update_pages():
    """ Updates list of connected streams in browser """
    try:  # attempt to read list of group names
        groups = current_app.database.read_all_groups()
    except Database.Error:
        groups = []
    print("GROUPS: ", type(groups))
    socketio.emit('update_pages', groups, namespace='/browser')


def update_files():
    """ Updates list of database files in browser """
    data_path = 'data/redis_dumps'
    try:  # attempt to get list of files in data directory
        files = [file for file in listdir(data_path) if isfile(join(data_path, file))]
    except Exception as e:
        print(e)
        files = []
    socketio.emit('update_files', files, namespace='/browser')


def update_buttons():
    """ Sends all button data stored in session """
    socketio.emit('update_buttons', current_app.buttons, namespace='/browser')


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
def connect():
    """ On connecting to the browser """
    refresh()  # send streams immediately on connecting


@socketio.on('disconnect', namespace='/browser')
def disconnect():
    """ On disconnecting from the browser """
    # print('Browser disconnected: {}'.format(request.sid))
    pass


####################################
# Handlers for browser buttons


@socketio.on('start', namespace='/browser')
@catch_errors
def start():
    """ start all streams """
    if current_app.database.ping():  # make sure database connected
        if current_app.database.live:  # live mode
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
    if not current_app.database.live:  # if in playback mode
        current_app.database.dump(save=False)  # dump database file
        return

    # live mode
    socketio.emit('stop', namespace='/streamers')  # send stop command to streamers
    filename = current_app.database.dump()  # dump database file
    log('Session Saved: {}'.format(filename))
    current_app.database.init()  # start new database
    socketio.emit('update', namespace='/streamers')  # request info update from streamers
    set_button('start', disabled=False)
    set_button('stop', disabled=True)
    sleep(0.1)
    refresh()


@socketio.on('refresh', namespace='/browser')
@catch_errors
def refresh():
    """ Refresh all data displayed in browser index """
    update_pages()
    update_files()
    update_buttons()
    get_database()


@socketio.on('playback', namespace='/browser')
@catch_errors
def playback():
    """ Switches back to playback mode for current database file """
    current_app.database.set_live(False)  # set database to playback mode
    log('Set database to Playback mode')
    set_button('live', hidden=False, disabled=False)
    set_button('playback', hidden=True)
    socketio.emit('update_header', 'Playback', namespace='/browser')
    refresh()


@socketio.on('live', namespace='/browser')
@catch_errors
def live():
    """ Switches back to current live database file """
    current_app.database.dump(save=False)  # remove loaded file
    current_app.database.init()  # init clean database
    current_app.database.set_live(True)  # set database to live mode
    log('Set database to Live mode')
    set_button('live', hidden=True)
    set_button('playback', hidden=False, disabled=False)
    socketio.emit('update_header', 'Connected Streams', namespace='/browser')
    refresh()


@socketio.on('load', namespace='/browser')
@catch_errors
def load(filename):
    """ Loads the given database file for playback """
    current_app.database.load_file(filename)
    log('Loaded "{}" to database'.format(filename))

    # don't allow database writes during playback of a loaded file
    current_app.database.set_write(False)
    current_app.database.set_live(False)  # set database on playback mode

    set_button('live', hidden=False, disabled=False, text='New Session')
    set_button('playback', disabled=True)
    log('Set database to Playback mode')

    # update page header with name of loaded file
    socketio.emit('update_header', 'Playback: {}'.format(filename), namespace='/browser')
    refresh()


@socketio.on('rename', namespace='/browser')
@catch_errors
def rename(data):
    """ Renames the selected file """
    old = data['filename']
    new = data['newname']
    check_filename(old)
    check_filename(new)
    current_app.database.rename_save(old, new)
    log('Renamed "{}" to "{}"'.format(old, new))
    refresh()


@socketio.on('delete', namespace='/browser')
@catch_errors
def delete(filename):
    """ Deletes the selected file """
    current_app.database.delete_save(filename)
    log('Deleted file "{}"'.format(filename))
    refresh()
