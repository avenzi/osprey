from flask import request, current_app, session
from app.main import socketio
from threading import Thread, Event

import ffmpeg
import numpy as np

# ffmpeg process to encode raw audio data into AAC format
ffmpeg_process = (
    ffmpeg
    .input('pipe:', format='f32le', ac=1)  # SoundDevice outputs Float-32, little endian by default.
    .output('pipe:', format='adts')  # AAC format
    .global_args("-loglevel", "quiet")
    .run_async(pipe_stdin=True, pipe_stdout=True)  # run asynchronously and pipe from/to stdin/stdout
)

events = {}  # {socket_id: event}

# TODO: These events start a new thread for each SocketIO that connects.
#  This thread streams data from that SESSION's associated database connection.
#  This means that if one session opens two tabs to view the same stream, data will be split.
#  Two different sessions, however, will read the same data independently.
#  This behavior is intended to be the same as the current Bokeh streams, even though it is not the most efficient.
#  At some point, I want to redo both the Bokeh streams (with a bokeh server) AND this video stream to make it so that
#   incoming sockets join a room for a given stream, and any other sockets wanting to see that same stream will just join
#   that room. This means both that data will not be read redundantly AND no data splitting will occur.
#  I haven't implemented that now because I want to wait until I know how to set up a Bokeh server.
#  At that point, I want to create some generalized method to implement this functionality for ANY data stream,
#   and simply apply it to both the Bokeh data and the video data.
#  This general method should take in the group name of a stream, and return the full html document for the browser.
#  .
#  Also I have my previous version of this in video_stream_events_room_version.py, however note that it
#   does NOT function as intended, because each incoming connection still uses it's own database object to retrieve
#   time information (start_time, elapsed_time, etc), but the actual streaming is done by the first Datbase connection
#   that enters the room. This means that the time display information between sessions will NOT be synced.
#  .
#  The solution to this (for both the Bokeh and video streams) will be to completely redo how the server requests data.
#  Rather than each session having an associated Database connection, rather each ROOM will have an associated connection.
#  Then, when a session requests data, the server will look for a ROOM streaming that data, if it exists.
#  The session can still have a default database connection to get information for the index page, but that connection
#   won't actually be used to read data, only metadata. It could even be a separate class designed for that purpose.
#  Two sessions both viewing the same redis instance could have the same associated "metadata" database connection.
#  This "metadata" Database connection could be the one to spawn the actual LiveDatabase or PlaybackDatabase connections
#   for each room, which then operate independently.
#  Just be careful that when a live database requests a stream, it will be put in a room already streaming that live database.
#  However, when a playback database requests a stream, it will be put in a room UNIQUE TO ITS OWN SESSION.
#  .
#  Also just a note (because I struggled with this before), a browser client socket does not need to know what session it's in.
#  All joining of rooms happen on the server side, so the socket does not even need to have that information.
#  The server just looks at the session ID of the incomming socket request and handles everything from there.


@socketio.on('start', namespace='/video_stream')
def start_video_stream(stream_ids):
    """
    Starts a streaming thread for each video stream and each session
    <stream_ids> is a dictionary of stream IDs given by the browser, containing keys 'video' and 'audio'
    """
    socket = request.sid  # socket ID

    # database associated with this session
    database = current_app.database_controller.get(session.sid)
    events[socket] = Event()  # create event
    events[socket].set()      # activate that event before the thread starts

    # run audio encoding thread
    Thread(target=encode_audio, args=(database, stream_ids, socket), name='AUDIO_ENCODE', daemon=False).start()
    # run streaming thread
    Thread(target=run_stream, args=(database, stream_ids, socket), name='VIDEO', daemon=False).start()


@socketio.on('disconnect', namespace='/video_stream')
def browser_disconnect():
    """ On disconnecting from the browser, clear event and stop streaming thread """
    socket = request.sid
    events[socket].clear()  # stop stream (unset threading event to stop loop)
    del events[socket]      # remove this event from the index of events


def encode_audio(database, stream_ids, socket):
    """
    Reads audio data from the database and encodes it,
    ready to be sent to a browser.
    Same arguments as run_video_stream
    """
    event = events[socket]
    video_id = stream_ids.get('video')
    audio_id = stream_ids.get('audio')

    if not audio_id:
        return

    while event.is_set():
        audio_data_dict = database.read_data(audio_id, max_time=10)
        if audio_data_dict:
            # put data in format able to be read by ffmpeg (each sample needs to be it's own array)
            data = audio_data_dict['data']
            for i in range(len(data)):
                data[i] = np.array(data[i])
            data = np.array(data)
            ffmpeg_process.stdin.write(data)  # feed raw data into ffmpeg
        socketio.sleep(0.1)


def run_stream(database, stream_ids, socket):
    """
    Reads video stream data until stopped.
    Should be run on a separate thread.
    <database> is the database to read the stream from
    <stream_id> is the database ID of the video stream
    <socket> is the SocketIO ID of the socket this thread should stream to.
        (Can't use request.sid because this thread is out of the request context)
    """
    event = events[socket]
    video_id = stream_ids.get('video')
    audio_id = stream_ids.get('audio')
    video_data = b''
    audio_data = b''

    while event.is_set():  # while event is set (while socket is connected)
        if video_id:
            try:
                video_data_dict = database.read_data(video_id, decode=False, max_time=10)
                if video_data_dict:
                    video_frames = video_data_dict['frame']  # get list of unread frames
                    video_data = b''.join(video_frames)  # concatenate all frames
            except Exception as e:
                print("Video stream failed to read from database. {}".format(e))
                break

        if audio_id:
            audio_data = ffmpeg_process.stdout.read(1024)
            if not audio_data:
                print("no encoded audio read from ffmpeg")
                socketio.sleep(1)

        print('video:', len(video_data), 'audio:', len(audio_data))

        # TODO: calculate duration of data read and send to Jmuxer?

        # package for browser
        data = {'video': video_data, 'audio': audio_data}

        socketio.emit('data', data, namespace='/video_stream', room=socket)  # send back to socket
        socketio.sleep(0.01)
