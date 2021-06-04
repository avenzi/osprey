from flask import request, current_app, g
from time import sleep

from app.main import socketio
from app import Database


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
    """ notified that a new streamer has initialized """
    try:
        info = current_app.database.read_info(stream_id)
    except Database.Error:
        print("Streamer initialized, but failed to get info for a stream with ID: {}".format(stream_id))
        return
    socketio.emit('init', info, namespace='/analyzer_client')  # give info to analyzer client


@socketio.on('update', namespace='/streamers')
def streamer_update(stream_id):
    """ notified that the streamer's info has updated """
    browser_refresh()


@socketio.on('log', namespace='/streamers')
def streamer_log(resp):
    """ On receiving logs from streamers, forward to the browser log """
    socketio.emit('log', resp, namespace='/browser')


######################################
# Browser buttons
# label: button name display
# command: socketIO message function to trigger
# tooltip: button hover text
BUTTONS = [{'label': 'Init',     'command': 'initialize', 'tooltip': 'Initialize the database'},
           {'label': 'Shutdown', 'command': 'shutdown',   'tooltip': 'Stop streamers and shutdown database'},
           {'label': 'Start',    'command': 'start',      'tooltip': 'Start all connected streamers'},
           {'label': 'Stop',     'command': 'stop',       'tooltip': 'Stop all connected streamers'},
           {'label': 'Refresh',  'command': 'refresh',    'tooltip': 'Refresh list of connected streams'}
           ]

# Handlers for browser buttons
@socketio.on('initialize', namespace='/browser')
def database_init():
    """ start database process """
    current_app.database.init()  # start database process
    sleep(0.1)  # give it sec to start up
    socketio.emit('log', 'Started Redis server', namespace='/browser')  # log on browser
    socketio.emit('init', namespace='/streamers')  # request init from streamers


@socketio.on('shutdown', namespace='/browser')
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
    """ refresh list of connected streams """
    try:
        info = current_app.database.get_all_info()
    except Database.Error:
        info = []

    socketio.emit('update', info, namespace='/browser')

