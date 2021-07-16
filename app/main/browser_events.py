from flask import current_app, session, request
from datetime import timedelta
from time import sleep

from lib.database import DatabaseError, DatabaseLoading

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
    database = get_database()
    if database.ping():  # make sure database connected
        if database.live:  # live mode
            log("Sending Start command to streamers")
            socketio.emit('start', namespace='/streamers')  # send start command to streamers
        else:  # playback mode
            log("Started playback")
        database.start()
        update_buttons()
    else:
        error('Cannot start streams - database ping failed')


@socketio.on('stop', namespace='/browser')
@catch_errors
def stop():
    """ Stop streams, dump database file to disk, start a clean database file """
    database = get_database()
    database.stop()
    if database.live:
        socketio.emit('stop', namespace='/streamers')  # send stop command to streamers
        filename = database.save()  # save database file (if live) and wipe contents
        log('Session Saved: {}'.format(filename))
        socketio.emit('update', namespace='/streamers')  # request info update from streamers

    else:  # playback
        log('Paused Playback')

    sleep(0.1)  # hopefully give time for database to get updates from streamers
    # todo: if we want to have confirmation of an update, we must check the info:updated column in redis and check the timestamp
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


@socketio.on('live', namespace='/browser')
@catch_errors
def live():
    """ Switches back to current live database  """
    log('Switching to live database')
    set_button('live', hidden=True)
    set_button('start', text='Start Streaming')
    set_button('stop', text='Stop all streams and save the file to disk')
    set_database()  # set database to live
    refresh()


@socketio.on('load', namespace='/browser')
@catch_errors
def load(filename):
    """ Loads the given database file for playback """
    log('Loading file...')
    set_database(filename)  # set a playback database for the given file

    n = 0
    while True:
        sleep(1)
        n += 1
        try:  # check if available
            get_database().ping(catch_error=False)
            break
        except DatabaseLoading as e:  # still loading
            error("Still loading file... ({})".format(n))
            sleep(5)
        except DatabaseError as e:  # lost connection (might have been aborted)
            error("Failed to load database: {}".format(e.__class__.__name__, e))
            return

    set_button('live', hidden=False, disabled=False, text='Back to live session')
    set_button('start', text='Start playback')
    set_button('stop', text='Stop playback')
    log('Loaded "{}" for playback'.format(filename))
    refresh()


@socketio.on('abort', namespace='/browser')
@catch_errors
def abort():
    """ Aborts loading a database file """
    get_database().kill()  # force kill currently loaded database
    if get_database().live:
        error("Force killing live database - some data may be lost")
        refresh()
    else:
        error("Force killing playback database")
        live()  # switch back to live


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


@socketio.on('stream_time', namespace='/browser')
@catch_errors
def stream_time(group):
    """ Get the current time information to display for the given stream """
    database = get_database()
    if not database:
        print("Database not found")
        return ""

    if not group:
        raise Exception("Stream time was requested, but no group ID was given")

    # all streams in this group
    streams = database.read_streams(group)
    if not streams:
        return

    display = ""
    for name, ID in streams.items():
        elapsed = database.get_elapsed_time(ID)  # time elapsed to far in seconds
        display += "{}: {}".format(name, str(timedelta(seconds=int(elapsed))))

        if not database.live:  # add total time of stream
            total = database.get_total_time(ID)
            display += " / {}".format(str(timedelta(seconds=int(total))))
        display += '<br>'

    socketio.emit('stream_time', display, namespace='/browser', room=request.sid)