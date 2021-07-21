from flask import request, current_app, session, copy_current_request_context
from flask_socketio import join_room, leave_room
from app.main import socketio
from threading import Thread, Event

# Maps to keep track of what socketIO connections are watching which video streams.
video_streams = {}  # {stream_ID: Threading_Event}
stream_counts = {}  # {stream_ID: number_of_clients}
browser_clients = {}  # {socketIO_SID: stream_ID}

# TODO: The video.html file loads information like the height and width of the video from the Jinja2 template.
#  Instead, that information should be sent vid SocketIO from this file instead - much cleaner and more flexible.
#  Also move all that JS to a dedicated .js file in /static


@socketio.on('start', namespace='/video_stream')
def start_video_stream(ID):
    """
    Looks for a threading event associated with this stream ID.
    If none is found, then create one and start streaming to a socketIO room with that ID.
    If there is one, add to the number of watching streams. The browser will connect to the existing stream in that room.
    """
    print("GOT VIDEO START REQUEST FROM: {}".format(request.sid))
    join_room(ID)  # put client in room with ID of stream ID
    if not video_streams.get(ID):  # no event associated with this stream
        print("NO EVENT FOR THIS STREAM: {}".format(ID))
        video_streams[ID] = Event()  # create event for this stream ID
        stream_counts[ID] = 0  # start count for this ID

        # run streaming thread
        db = current_app.database_controller.get(session.sid)
        video_streams[ID].set()  # set event to run stream
        print("STARTING VIDEO STREAM THREAD: {}".format(ID))
        Thread(target=run_video_stream, args=(db, ID), name='VIDEO', daemon=False).start()
        # TODO: Should I be using a gevent spawn here instead?

    print("EVENT EXISTS FOR THIS STREAM: {}".format(ID))
    # if stream already exists
    video_streams[ID].set()  # set event if not already
    stream_counts[ID] += 1  # increment number of clients watching this stream
    browser_clients[request.sid] = ID  # associate this socket connection to this stream


@socketio.on('disconnect', namespace='/video_stream')
def browser_disconnect():
    """ On disconnecting from the browser, clear event and stop streaming thread """
    print("DISCONNECTED: {}".format(request.sid))
    ID = browser_clients[request.sid]  # get stream ID associated with this socket connection

    stream_counts[ID] -= 1  # decrement number of watching clients
    if stream_counts[ID] == 0:  # last one
        video_streams[ID].clear()  # stop stream (unset threading event to stop loop)
        print("EVENT CLEARED: {}".format(ID))

    leave_room(ID)  # remove this client from the room


def run_video_stream(database, ID):
    """
    Runs a video stream until stopped
    Should be run on a separate thread
    <ID> is the ID of the stream
    <event> is the threading event used to stop the stream
    """
    print("STARTED VIDEOS STREAM: {}".format(ID))
    event = video_streams[ID]
    while event.is_set():  # while event is set (while socket is connected)
        try:
            data_dict = database.read_data(ID, numerical=False, decode=False)
            if not data_dict:
                socketio.sleep(0.1)
                continue
        except Exception as e:
            print("Video stream failed to read from database. {}".format(e))
            break
        frames = data_dict['frame']  # get list of unread frames
        data = b''.join(frames)  # concatenate all frames
        socketio.emit('data', data, namespace='/video_stream', room=ID)
    print("STREAM WHILE LOOP ENDED: {}".format(ID))
