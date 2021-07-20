from app.main import socketio

from app.main.browser_events import log, update_pages

"""
Namespaces:
    UUID of stream: only that stream
    "/analyzers": all analyzer streams
    "/streamers": all streams (including analyzers)
"""

# todo: Idea to allow client sockets to join certain rooms tied to the database they are viewing:
#  Add a socket message handler that echos the socket's session ID, so it knows what session that is.
#  Also emit some info like what databse they are viewing - that will allow them to a join a room for that too.
#  This way, all tabs of a single session can receive the same data, and all sessions viewing the same database can receive the same data.


@socketio.on('connect', namespace='/streamers')
def connect():
    """ On disconnecting from a streamer """
    # print("A Streamer connected")
    pass


@socketio.on('disconnect', namespace='/streamers')
def disconnect():
    """ On disconnecting from a streamer """
    # print("A Streamer disconnected")
    pass


@socketio.on('init', namespace='/streamers')
def streamer_init(stream_id):
    """ notified when a new stream has been initialized """
    # tell waiting analyzers to check to see if this is their target
    socketio.emit('check_database', stream_id, namespace='/analyzers')


@socketio.on('update', namespace='/streamers')
def streamer_update(stream_id):
    """ notified that the streamer's info has updated """
    update_pages(room='live')  # update pages of live streams


@socketio.on('log', namespace='/streamers')
def streamer_log(resp):
    """ On receiving logs from streamers, forward to all browser logs """
    log(resp, everywhere=True)
