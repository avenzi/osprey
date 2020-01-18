"""Audio Recording Socket.IO Example

Implements server-side audio recording.
"""
"""
import os
import uuid
import wave
from flask import Blueprint, current_app, session, url_for, render_template
from flask_socketio import emit
from capstone import socketio

@socketio.on('start-recording', namespace='/audio')
def start_recording(options):
    id = uuid.uuid4().hex  # server-side filename
    session['wavename'] = id + '.wav'
    wf = wave.open(current_app.config['FILEDIR'] + session['wavename'], 'wb')
    wf.setnchannels(options.get('numChannels', 1))
    wf.setsampwidth(options.get('bps', 16) // 8)
    wf.setframerate(options.get('fps', 44100))
    session['wavefile'] = wf


@socketio.on('write-audio', namespace='/audio')
def write_audio(data):
    session['wavefile'].writeframes(data)


@socketio.on('end-recording', namespace='/audio')
def end_recording():
    emit('add-wavefile', url_for('static',
                                 filename='_files/' + session['wavename']))
    session['wavefile'].close()
    del session['wavefile']
    del session['wavename']
"""
