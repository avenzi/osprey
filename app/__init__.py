#from eventlet import monkey_patch as monkey_patch
#monkey_patch()

from flask import Flask, send_from_directory
import os
import json

from lib.database import Database


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY='thisisthesecretkeytotheflaskserver')

    # get database config options
    try:
        with open('config/server_streamer_config.json') as file:
            config = json.load(file)
    except Exception as e:
        raise Exception('No database config file found. Please run the appropriate setup script first.')

    app.database = Database(config['SERVER_IP'], config['DB_PORT'], config['DB_PASS'])

    # add basic favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # register blueprints and sockets
    from app.main import auth
    app.register_blueprint(auth)

    from app.main import streams
    app.register_blueprint(streams)
    app.add_url_rule('/', endpoint='index')

    from app.main import socketio
    socketio.init_app(app, async_mode='eventlet')
    return app


