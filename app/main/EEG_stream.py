from flask import request, current_app, g, session

from app.main import socketio


@socketio.on('eeg_info', namespace='/streamers')
def eeg_info(data):
    """ Initial info received from an EEG streamer """
    session['eeg_stream'] = data
    print(type(data), data)
