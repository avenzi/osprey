from flask import request, current_app, copy_current_request_context
from flask_socketio import join_room, leave_room
from app.main import socketio
from threading import Thread, Event
from app import Database

# Maps to keep track of what socketIO connections are watching which video streams.
video_streams = {}  # {stream_ID: Threading_Event}
stream_counts = {}  # {stream_ID: number_of_clients}
browser_clients = {}  # {socketIO_SID: stream_ID}


@socketio.on('start', namespace='/video_stream')
def start_video_stream(ID):
    """
    Looks for a threading event associated with this stream ID.
    If none is found, then create one and start streaming to a socketIO room with that ID.
    If there is one, add to the number of watching streams. The browser will connect to the existing stream in that room.
    """
    join_room(ID)  # put client in room with ID of stream ID
    if not video_streams.get(ID):  # no event associated with this stream
        video_streams[ID] = Event()  # create event for this stream ID
        stream_counts[ID] = 0  # start count for this ID

        # run streaming thread
        Thread(target=run_video_stream, args=(current_app.database, ID), name='VIDEO', daemon=False).start()
        # TODO: Should I be using a gevent spawn here instead?

    # if stream already exists
    video_streams[ID].set()  # set event if not already
    stream_counts[ID] += 1  # increment number of clients watching this stream
    browser_clients[request.sid] = ID  # associate this socket connection to this stream


@socketio.on('disconnect', namespace='/video_stream')
def browser_disconnect():
    """ On disconnecting from the browser, clear event and stop streaming thread """
    ID = browser_clients[request.sid]  # get stream ID associated with this socket connection

    stream_counts[ID] -= 1  # decrement number of watching clients
    if stream_counts[ID] == 0:  # last one
        video_streams[ID].clear()  # stop stream (unset threading event to stop loop)

    leave_room(ID)  # remove this client from the room


def run_video_stream(database, ID):
    """
    Runs a video stream until stopped
    Should be run on a separate thread
    <ID> is the ID of the stream
    <event> is the threading event used to stop the stream
    """
    event = video_streams[ID]
    while True:
        event.wait()  # stream only when even is set
        try:
            data_dict = database.read_data(ID, numerical=False, decode=False)
            if not data_dict:
                socketio.sleep(0.1)
                continue
        except Exception as e:
            print("Failed to read from database. {}".format(e))
            break
        frames = data_dict['frame']  # get list of unread frames
        data = b''.join(frames)  # concatenate all read frames
        try:
            socketio.emit('data', data, namespace='/video_stream', room=ID)
        except Exception as e:
            print("Failed to emit video stream to browser. {}".format(e))
            break

        #socketio.sleep(1)

