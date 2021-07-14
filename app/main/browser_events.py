from flask import current_app, session, request
from time import sleep

from app.main import socketio

from app.main.utils import (
    log, error, catch_errors,
    set_database, get_database, set_button,
    update_pages, update_files, update_buttons, update_text,
    check_filename
)


@socketio.on('connect', namespace='/browser')
@catch_errors
def connect():
    """ On connecting to the browser """
    print("SESSION CONNECT: {}".format(session.sid))
    print(session['buttons'])
    if not get_database():  # if no current session database
        set_database()  # set to a live database connection
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
    sleep(0.1)  # hopefully give time for database to get updates from streamers
    # todo: if we want to have confirmation of an update, we must check the info:updated column in redis
    #  we can't sent a message through socketIO because they will be received in a different session with no way
    #  to know what session to send that info to.
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
