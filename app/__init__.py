#from eventlet import monkey_patch as monkey_patch
#monkey_patch()

from flask import Flask, send_from_directory
from flask_session import Session
from redis import from_url
import os
import json

from lib.database import DatabaseController


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'thisisthesecretkeyfortheflaskserver'
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = from_url('redis://localhost:6379')
    Session(app)  # initialize server side session

    # interface to database connections
    app.database_controller = DatabaseController(live_path='data/live', saved_path='data/saved')

    # add basic favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # server static js files
    @app.route('/js/<filename>')
    def serve_js(filename):
        return send_from_directory(os.path.join(app.root_path, 'static', 'js'), filename)

    # register blueprints and sockets
    from app.main import auth
    app.register_blueprint(auth)

    from app.main import streams
    app.register_blueprint(streams)
    app.add_url_rule('/', endpoint='index')

    from app.main import socketio
    socketio.init_app(app, async_mode='eventlet', manage_session=False)
    # manage_sessions means that the socketIO and HTTP sessions will be the same
    return app


