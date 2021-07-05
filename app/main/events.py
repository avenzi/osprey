from flask import request, current_app, g
from time import sleep

from os import listdir
from os.path import isfile, join

from app.main import socketio
from app import Database

"""
Namespaces:
    UUID of stream: only that stream
    "/analyzers": all analyzer streams
    "/streamers": all streams (including analyzers)
"""


@socketio.on('connect', namespace='/browser')
def browser_connect():
    """ On connecting to the browser """
    # print('Browser connected: {}'.format(request.sid))
    browser_refresh()  # send streams immediately on connecting


@socketio.on('disconnect', namespace='/browser')
def browser_disconnect():
    """ On disconnecting from the browser """
    # print('Browser disconnected: {}'.format(request.sid))
    pass


################################
# Streamer messages

@socketio.on('connect', namespace='/streamers')
def streamer_connect():
    """ On disconnecting from a streamer """
    #print("A Streamer connected")
    pass


@socketio.on('disconnect', namespace='/streamers')
def streamer_disconnect():
    """ On disconnecting from a streamer """
    #print("A Streamer disconnected")
    pass


@socketio.on('init', namespace='/streamers')
def streamer_init(stream_id):
    """ notified when a new stream has been initialized """
    # tell waiting analyzers to check to see if this is their target
    socketio.emit('check_database', stream_id, namespace='/analyzers')


@socketio.on('update', namespace='/streamers')
def streamer_update(stream_id):
    """ notified that the streamer's info has updated """
    browser_update_pages()


@socketio.on('log', namespace='/streamers')
def streamer_log(resp):
    """ On receiving logs from streamers, forward to the browser log """
    socketio.emit('log', resp, namespace='/browser')


######################################

# Handlers for browser buttons
@socketio.on('initialize', namespace='/browser')
def database_init():
    """ start database process """
    current_app.database.init()  # start database process
    sleep(0.1)  # give it sec to start up
    socketio.emit('log', 'Started Redis server', namespace='/browser')  # log on browser
    socketio.emit('update', namespace='/streamers')  # request update from streamers


@socketio.on('save', namespace='/browser')
def database_shutdown():
    """ stop database process and dump data """
    socketio.emit('stop', namespace='/streamers')  # stop streams first
    current_app.database.shutdown()  # stop database process
    socketio.emit('log', 'Shut down Database', namespace='/browser')
    sleep(0.1)
    browser_refresh()


@socketio.on('start', namespace='/browser')
def browser_start():
    """ start all streams """
    if current_app.database.ping():  # make sure database connected
        socketio.emit('start', namespace='/streamers')  # send start command to streamers
    else:
        socketio.emit('log', 'Cannot start streams - database not initialized', namespace='/browser')


@socketio.on('stop', namespace='/browser')
def browser_stop():
    """ Stop streams """
    # send stop command to streamers
    socketio.emit('stop', namespace='/streamers')


@socketio.on('refresh', namespace='/browser')
def browser_refresh():
    """ Refresh all data displayed in browser index """
    browser_update_pages()
    browser_update_files()
    browser_update_buttons()


@socketio.on('live', namespace='/browser')
def browser_live():
    """ Switches back to current live database file """
    print("RECEIVED LIVE")


@socketio.on('load', namespace='/browser')
def browser_live(filename):
    """ Loads the given database file for playback """
    print("RECEIVED LOAD: {}".format(filename))


@socketio.on('rename', namespace='/browser')
def browser_live(filename):
    """ Renames the selected file """
    print("RECEIVED RENAME: {}".format(filename))


@socketio.on('delete', namespace='/browser')
def browser_live(filename):
    """ Deletes the selected file """
    print("RECEIVED DELETE: {}".format(filename))


def browser_update_pages():
    """ Updates list of connected streams in browser """
    try:  # attempt to read list of group names
        groups = current_app.database.read_all_groups()
    except Database.Error:
        groups = []
    socketio.emit('update_pages', groups, namespace='/browser')


def browser_update_files():
    """ Updates list of database files in browser """
    data_path = 'data'
    try:  # attempt to get list of files in data directory
        files = [file for file in listdir(data_path) if isfile(join(data_path, file))]
    except Exception as e:
        print(e)
        files = []
    socketio.emit('update_files', files, namespace='/browser')


def browser_update_buttons():
    """ Updates state of buttons in browser """
    buttons = [{'test':'testvalue', 'test2':'testvalue2'}]
    socketio.emit('update_buttons', buttons, namespace='/browser')