from flask import request, current_app, g
from datetime import datetime
from time import sleep
import os

from . import socketio
from .stream_routes import get_redis


def get_time():
    """ Return human readable time for file names """
    return datetime.now().strftime("%-H:%-M:%-S:%f")


@socketio.on('connect', namespace='/browser')
def browser_connect():
    """ On connecting to the browser """
    print('Browser connected: {}'.format(request.sid))
    browser_command('REFRESH')  # send streams immediately on connecting


@socketio.on('disconnect', namespace='/browser')
def browser_disconnect():
    """ On disconnecting from the browser """
    print('Browser disconnected: {}'.format(request.sid))


@socketio.on('connect', namespace='/streamer')
def streamer_connect():
    """ On disconnecting from a streamer """
    # TODO: this method does not seem to trigger. Not a big deal, but it should.
    print("A Streamer connected")


@socketio.on('disconnect', namespace='/streamer')
def streamer_disconnect():
    """ On disconnecting from a streamer """
    # TODO: same issue as streamer_connect()
    print("A Streamer disconnected")


@socketio.on('log', namespace='/streamers')
def streamer_response(resp):
    """ On receiving logs from streamers, forward to the browser log """
    socketio.emit('log', resp, namespace='/browser')


@socketio.on('command', namespace='/browser')
def browser_command(comm):
    """ Commands received from the browser """
    if comm == 'START':
        if not get_redis():  # attempt to connect
            os.system("redis-server config/redis.conf")
            socketio.emit('log', 'Started Redis server', namespace='/browser')
            sleep(0.1)
        socketio.emit('command', 'START', namespace='/streamers')  # send start command to streamers

    elif comm == 'STOP':
        # Stop redis server and move dump file
        if get_redis():
            current_app.redis.shutdown(save=True)
            os.system("mv data/dump.rdb data/redis_dumps/{}.rdb".format(get_time()))
        socketio.emit('log', 'Shutdown Redis and dumped database', namespace='/browser')
        socketio.emit('command', 'STOP', namespace='/streamers')  # send stop command to streamers

    elif comm == 'REFRESH':
        # refresh list of connected streams
        stream_names = []
        if get_redis():
            for key in g.redis.execute_command('keys info:*'):
                stream_names.append(g.redis.execute_command('hget {} name'.format(key)))
        socketio.emit('update', stream_names, namespace='/browser')

    else:
        socketio.emit('log', "Unknown Command: {}".format(comm), namespace='/browser')

