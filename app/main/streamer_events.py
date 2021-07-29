from app.main import socketio

from app.main.browser_events import log, error, update_pages

"""
Namespaces:
    UUID of stream: only that stream
    "/analyzers": all analyzer streams
    "/streamers": all streams (including analyzers)
"""


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


@socketio.on('update', namespace='/streamers')
def streamer_update(stream_id):
    """ notified that the streamer's info has updated """
    socketio.emit('check_database', stream_id, namespace='/analyzers')
    print("[Sent check_database message]")
    # todo: at the moment this doesn't do anything because there is no specific room for the live stream,
    #  and this handler doesn't know what sessions are viewing the live stream.
    #  This will only work once these rooms have been implemented, see the comment in video_stream_events.py
    update_pages(room='live')  # update pages of live streams


@socketio.on('log', namespace='/streamers')
def streamer_log(resp):
    """ On receiving logs from streamers, forward to all browser logs """
    log(resp, everywhere=True)


@socketio.on('error', namespace='/streamers')
def streamer_error(resp):
    """ On receiving error logs from streamers, forward to all browser logs """
    error(resp, everywhere=True)