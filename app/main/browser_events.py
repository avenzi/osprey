from flask import current_app, session, request
import json
from datetime import timedelta
from time import sleep, time



from lib.database import DatabaseError, DatabaseBusyLoadingError, DatabaseTimeoutError, DatabaseConnectionError

from app.main import socketio

from app.main.utils import (
    log, info, warn, error, catch_errors,
    set_database, get_database, set_button,
    update_pages, update_files, update_buttons, request_update,
    check_filename, bytes_to_human
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
# Handlers for browser socketIO messages and buttons

# Todo: make sure that no leftover data from a previous stream is in the database.
#  It messes up the plots when reviewing the data.

@socketio.on('start', namespace='/browser')
@catch_errors
def start():
    """ start all streams """
    database = get_database()
    if not database:
        error("Could not start streams - database not found")
        return
    database.ping()
    if database.live:  # live mode
        info("Sending Start command to streamers")
        socketio.emit('start', namespace='/streamers')  # send start command to streamers
    else:  # playback mode
        info("Started playback")
    database.start()


@socketio.on('stop', namespace='/browser')
@catch_errors
def stop():
    """ Stop streams, dump database file to disk, start a clean database file """
    database = get_database()
    database.stop()
    if database.live:
        socketio.emit('stop', namespace='/streamers')  # send stop command to streamers
        try:
            filename = database.save()  # save database file (if live) and wipe contents
        except Exception as e:
            error("Failed automatic database export.")
            raise e
        info('Session Exported to file: {}'.format(filename))
    else:  # playback
        log('Paused Playback')
    refresh()


@socketio.on('refresh', namespace='/browser')
@catch_errors
def refresh():
    """ Refresh all data displayed in browser index """
    request_update()
    update_pages()
    update_files()
    update_buttons()


@socketio.on('live', namespace='/browser')
@catch_errors
def live():
    """ Switches back to current live database  """
    log('Switching to live database...')
    set_button('start', text='Start Streaming')
    set_button('stop', text='Stop all streams and save the file to disk')
    set_database()  # set database to live
    info('Live database loaded.')
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
            get_database().ping()
            break
        except DatabaseBusyLoadingError as e:  # still loading
            warn("Still loading file... ({})".format(n))
            sleep(5)
        except DatabaseError as e:  # lost connection (might have been aborted)
            error("Failed to load database (ping failed): {}".format(e.__class__.__name__, e))
            return

    set_button('live', text='Back to live session')
    set_button('start', text='Start playback')
    set_button('stop', text='Stop playback')
    info('Loaded "{}" for playback'.format(filename))
    refresh()


@socketio.on('abort', namespace='/browser')
@catch_errors
def abort():
    """ Aborts loading a database file """
    get_database().kill()  # force kill currently loaded database
    if get_database().live:
        warn("Force killing live database - some data may be lost")
        refresh()
    else:
        warn("Force killing playback database")
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
    info('Renamed "{}" to "{}"'.format(old, new))
    refresh()


@socketio.on('delete', namespace='/browser')
@catch_errors
def delete(filename):
    """ Deletes the selected file """
    current_app.database_controller.delete_save(filename)
    warn('Deleted file "{}"'.format(filename))
    refresh()


@socketio.on('wipe', namespace='/browser')
@catch_errors
def wipe():
    """
    Wipes the data contents of the database, if live.
    Then requests an update from the streamers.
    """
    database = get_database()
    if not database:
        error("No database found")
        return
    if not database.live:
        error("Cannot wipe contents of playback file - use the 'Delete' button instead to remove the file.")
        return
    database.wipe()
    warn("Wiped all data from streams.")
    refresh()


@socketio.on('info', namespace='/browser')
@catch_errors
def database_info(data):
    """ Sends the info dict from the requested data stream """
    database = get_database()
    if not database:
        return
    group_name = data['group']
    stream_name = data['stream']

    # get info dict for this stream
    group_info = database.get_group(group_name, stream_name)

    # Send playback speed (multiplier).
    # Note that right now, only the video stream needs this information to set the HTML5 MediaElement playback speed.
    if not database.live:
        group_info['speed'] = database.playback_speed
    else:
        group_info['speed'] = 1

    socketio.emit('info', group_info, namespace='/browser', room=request.sid)


######################################
# Handler for status polling messages

@socketio.on('status', namespace='/browser')
@catch_errors
def status():
    """
    Emits a data dict with status information to be displayed
    """
    db = get_database()
    data = {
        'source': database_source(db),
        'streaming': database_status(db),
        'save': database_save_time(db),
        'memory': database_memory_usage(db)
    }
    socketio.emit('update_status', data, namespace='/browser', room=request.sid)


def database_source(database):
    """ Returns the database name to display """
    if not database:
        return "No Database Found"
    if database.live:
        return "Live Stream"
    else:  # playback
        return database.file


def database_status(database):
    """ Returns a string representing the database status """
    if not database:
        return "---"

    try:
        database.ping()  # raises error if problems
    except DatabaseBusyLoadingError:
        return "Loading..."
    except DatabaseTimeoutError:
        return "Not Responding..."
    except DatabaseConnectionError:
        return "Disconnected"
    except Exception as e:
        print("Database Status Error: {}: {}".format(e.__class__.__name__, e))
        return "err"

    if database.is_streaming():
        if database.live:
            return "Streaming"
        else:  # playback mode
            return "Streaming ({}x speed)".format(database.playback_speed)
    else:
        if database.live:
            return "Idle"
        else:  # playback mode
            return "Paused"


def database_save_time(database):
    """ last database save time """
    blank = "--:--:--"
    if not database:
        return blank
    try:
        if database.live:
            t = database.time_since_save()
            return str(timedelta(seconds=t)) + 's ago'
        else:
            return blank
    except:
        return "err"


def database_memory_usage(database):
    """ Total memory usage of the database """
    # todo: This metric is slightly disingenuous, as it displays the total memory usage of Redis
    #  alone out of the total memory available in the system. Importantly the memory used does not
    #  include that of any other processes, like the many python processes running alongside.
    #  This means that the total memory "available for the Redis server" is less than that displayed.
    #  To fix this, should we display the total memory used on the system as a whole, not just by Redis?
    #  Or maybe display Redis's memory usage, but only display the memory not being used by other processes?

    # Todo: implement a fail-safe to automatically stop the streams if memory usage gets to high?

    if not database:
        return "---"
    try:
        size = database.memory_usage()
        available = database.memory_available()
        return "{} / {}".format(bytes_to_human(size), bytes_to_human(available))
    except:
        return 'err'


######################################
# Handler for events used in stream pages
@socketio.on('stream_time', namespace='/browser')
@catch_errors
def stream_time(group):
    """ Return a human-readable string with current time information to display for the given stream """
    database = get_database()
    if not database:
        print("Database not found")
        return ""

    if not group:
        raise Exception("Stream time was requested, but no group ID was given")

    # all streams in this group
    streams = database.get_streams(group)
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


@socketio.on('custom_functions', namespace='/browser')
@catch_errors
def custom_functions(group):
    """ Request for a list of available custom functions and the currently selected functions for this stream """
    database = get_database()
    if not database:
        print("Database not found")
        return

    # id of Transform analyzer in this group
    ID = database.get_group(group, 'Transformed')['id']

    # read JSON encoded dictionary from database
    json_string = database.get_info(ID, 'pipeline')
    if not json_string:
        print("NO JSON FOUND")
        return
    data = json.loads(json_string)
    print("READING PIPELINE FROM DATABASE")
    print(data)

    # emit back to browser
    socketio.emit('custom_functions', data, namespace='/browser', room=request.sid)


@socketio.on('update_pipeline', namespace='/browser')
@catch_errors
def update_pipeline(data):
    """
    Browser updated the functions in the pipeline for this page.
    Updates this information in the database which can then be retrieved by custom_functions().
    """
    database = get_database()
    if not database:
        print("Database not found")
        return

    group = data['group']
    pipeline = data['pipeline']

    # id of Transform analyzer in this group
    ID = database.get_group(group, 'Transformed')['id']
    print("ID OF TRANSFORM ANALYZER: ", ID)
    socketio.emit('json', pipeline, namespace='/'+ID)






