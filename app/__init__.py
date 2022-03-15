import os

#from eventlet import monkey_patch
#monkey_patch()

from flask import Flask, send_from_directory
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from redis import from_url

from lib.database import DatabaseController
from server.interface import interface  # import the customized interface object


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'thisisthesecretkeyfortheflaskserver'
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = from_url('redis://localhost:6379')
    app.config['UPLOAD_FOLDER'] = 'local/pipelines'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000  # 16 MB

    # somehow fixes problems that occur when hosting behind proxy with SSL
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # initialize server side session
    Session(app)

    # interface to database connections (for prod: '3.131.117.61')
    app.database_controller = DatabaseController(live_path='data/live', saved_path='data/saved', public_ip='localhost')
    app.interface = interface  # allow the app to access to the customized interface object

    # register blueprints and sockets
    from app.main import auth
    app.register_blueprint(auth)

    from app.main import streams
    app.register_blueprint(streams)
    app.add_url_rule('/', endpoint='index')

    from app.main import socketio
    socketio.init_app(app, async_mode='eventlet', manage_session=False)
    # manage_sessions=False means that the socketIO and HTTP sessions will be the same

    return app


