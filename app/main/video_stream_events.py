from flask import request, current_app, session, copy_current_request_context
from flask_socketio import join_room, leave_room
from app.main import socketio
from threading import Thread, Event

# Maps to keep track of what socketIO connections are watching which video streams.
rooms = {}  # {socketIO_SID: room_ID}
room_events = {}  # {room_ID: Threading_Event}
room_counts = {}  # {room_ID: number_of_clients}


# TODO: The video.html file loads information like the height and width of the video from the Jinja2 template.
#  Instead, that information should be sent vid SocketIO from this file instead - much cleaner and more flexible.
#  Also move all that JS to a dedicated .js file in /static


@socketio.on('start', namespace='/video_stream')
def start_video_stream(stream_id):
    """
    Creates a room for each video stream.
    IF the stream is from a live database, that room can be joined from any session.
    If the stream is from a playback database, that room can only be joined from that session.
    Starts a new thread for each room that emits data from the database.
    """
    session_id = session.sid  # Server session ID
    socket_id = request.sid   # SocketIO session ID

    # database associated with this session
    database = current_app.database_controller.get(session_id)
    if database.live:
        room_id = stream_id  # join room for that live stream ID (can be seen by any session)
    else:  # playback
        room_id = stream_id+session_id  # join room unique to that stream and session.

    join_room(room_id)
    rooms[socket_id] = room_id  # associate this socket connection to this room (to lookup when it disconnects)
    print("GOT VIDEO START REQUEST FROM: {}".format(room_id[:10]))
    if not room_events.get(room_id):  # no event associated with this room
        print("NO EVENT FOR THIS ROOM: {}".format(room_id[:10]))
        room_events[room_id] = Event()  # create event for this room
        room_events[room_id].set()      # activate that event before the thread starts
        room_counts[room_id] = 1        # start count for this room at 1

        # run streaming thread
        print("STARTING VIDEO STREAM THREAD: {}".format(room_id[:10]))
        Thread(target=run_video_stream, args=(database, stream_id, room_id), name='VIDEO', daemon=False).start()
        # TODO: Should I be using a gevent spawn here instead?

    else:  # if this room already exists
        print("EVENT EXISTS FOR THIS ROOM: {}".format(room_id[:10]))
        room_events[room_id].set()  # set event if not already
        room_counts[room_id] += 1  # increment number of clients watching this stream


@socketio.on('disconnect', namespace='/video_stream')
def browser_disconnect():
    """ On disconnecting from the browser, clear event and stop streaming thread """
    socket_id = request.sid  # SocketIO session ID
    room_id = rooms[socket_id]  # get room associated with this socket connection
    print("DISCONNECTED room {}".format(room_id[:10]))
    room_counts[room_id] -= 1  # decrement number of clients in that room
    if room_counts[room_id] == 0:  # was the last one in there
        room_events[room_id].clear()  # stop stream (unset threading event to stop loop)
        del room_events[room_id]  # remove this event from the room
        print("EVENT CLEARED: {}".format(room_id[:10]))
    # No need to leave the room - SocketIO does this automatically on disconnect


def run_video_stream(database, stream_id, room_id):
    """
    Reads video stream data until stopped.
    Should be run on a separate thread.
    <database> is the database to read the stream from
    <stream_id> is the database ID of the video stream
    <room_id> is the ID of the SocketIO room that this thread serves
    """
    print("STARTED VIDEOS STREAM: {}".format(room_id[:10]))
    event = room_events[room_id]
    while event.is_set():  # while event is set (while socket is connected)
        try:
            data_dict = database.read_data(stream_id, numerical=False, decode=False)
            if not data_dict:  # no data is returned
                socketio.sleep(0.5)
                continue
        except Exception as e:
            print("Video stream failed to read from database. {}".format(e))
            break
        frames = data_dict['frame']  # get list of unread frames
        data = b''.join(frames)  # concatenate all frames
        socketio.emit('data', data, namespace='/video_stream', room=room_id)
    print("STREAM WHILE LOOP ENDED: {}".format(room_id[:10]))
