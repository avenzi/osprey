from flask import request, current_app, session
from app.main import socketio
from threading import Thread, Event
from app.main.utils import add_ADTS_header

events = {}  # {socket_id: event}

# TODO: These event start a new thread for each SocketIO that connects.
#  This thread streams data from that SESSION's associated database connection.
#  This means that if one session opens two tabs to view the same stream, data will be split.
#  Two different sessions, however, will read the same data independently.
#  This behavior intended to be the same as the current Bokeh streams, even though it is not the most efficient.
#  At some point, I want to redo both the Bokeh streams (with a bokeh server) AND this video stream to make it so that
#   incoming sockets join a room for a given stream, and any other sockets wanting to see that same stream will just join
#   that room. This means both that data will not be read redundantly AND no data splitting will occur.
#  I haven't implemented that now because I want to wait until I know how to set up a Bokeh server.
#  At that point, I want to create some generalized method to implement this functionality for ANY data stream,
#   and simply apply it to both the Bokeh data and the video data.
#  This general method should take in the group name of a stream, and return the full html document for the browser.
#  .
#  Also I have my previous version of this in video_stream_events_room_version.py, however not that it
#   does NOT function as intended, because each incoming connection still uses it's own database object to retrieve
#   time information (start_time, elapsed_time, etc), but the actual streaming is done by the first Datbase connection
#   that enters the room. This means that the time display information between sessions will NOT be synced.
#  .
#  The solution to this (for both the Bokeh and video streams) will be to completely redo how the server requests data.
#  Rather than each session having an associated Database connection, rather each ROOM will have an associated connection.
#  Then, when a session requests data, the server will look for a ROOM streaming that data, if it exists.
#  The session can still have a default database connection to get information for the index page, but that connection
#   won't actually be used to read data, only metadata. It could even be a separate class designed for that purpose.
#  To sessions both viewing the same redis instance could have the same associated "metadata" database connection.
#  This "metadata" Database connection could be the one to spawn the actual LiveDatabase or PlaybackDatabase connections
#   for each room, which then operate independently.
#  Just be careful that when a live database requests a stream, it will be put in a room already streaming that live database.
#  However, when a playback database requests a stream, it will be put in a room UNIQUE TO ITS OWN SESSION.
#  .
#  Also just a note (because I struggled with this before), a browser client socket does not need to know what session it's in.
#  All joining of rooms happen on the server side, so the socket does not even need to have that information.


@socketio.on('start', namespace='/video_stream')
def start_video_stream(stream_ids):
    """ Starts a streaming thread for each video stream and each session """
    socket = request.sid  # socket ID

    # database associated with this session
    database = current_app.database_controller.get(session.sid)
    events[socket] = Event()  # create event
    events[socket].set()      # activate that event before the thread starts

    # run streaming thread
    Thread(target=run_video_stream, args=(database, stream_ids, socket), name='VIDEO', daemon=False).start()


@socketio.on('disconnect', namespace='/video_stream')
def browser_disconnect():
    """ On disconnecting from the browser, clear event and stop streaming thread """
    socket = request.sid
    events[socket].clear()  # stop stream (unset threading event to stop loop)
    del events[socket]      # remove this event from the index of events


def run_video_stream(database, stream_ids, socket):
    """
    Reads video stream data until stopped.
    Should be run on a separate thread.
    <database> is the database to read the stream from
    <stream_id> is the database ID of the video stream
    <socket> is the SocketIO ID of the socket this thread should stream to.
        (Can't use request.sid because this thread is out of the request context)
    """
    event = events[socket]
    video_id = stream_ids['video']
    audio_id = stream_ids['audio']
    while event.is_set():  # while event is set (while socket is connected)
        try:
            video_data_dict = database.read_data(video_id, decode=False, max_time=10)
        except Exception as e:
            print("Video stream failed to read from database. {}".format(e))
            break

        try:
            audio_data_dict = database.read_data(audio_id, decode=False, max_time=10)
            pass
        except Exception as e:
            print("Video stream failed to read from database. {}".format(e))
            break

        video_data = b''
        if video_data_dict:
            video_frames = video_data_dict['frame']  # get list of unread frames
            video_data = b''.join(video_frames)  # concatenate all frames

        audio_data = b''
        if audio_data_dict:
            audio_frames = audio_data_dict['data']  # get list of unread audio data
            audio_data = b''.join(audio_frames)  # concatenate all data
        print('gonna add ADTS header...')
        audio_data = add_ADTS_header(audio_data)  # prepend ADTS header for Jmuxer
        print('added ADTS header')

        if not video_data_dict and not audio_data_dict:  # no data is returned
            socketio.sleep(0.1)
            continue

        # package for browser
        data = {'video': video_data, 'audio': audio_data}

        socketio.emit('data', data, namespace='/video_stream', room=socket)  # send back to socket
        socketio.sleep(1)
