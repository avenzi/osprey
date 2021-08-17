from flask import Flask
from flask_socketio import SocketIO, send_from_directory


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__)

    @app.route('/index', methods=['GET', 'POST'])
    def flask_page():
        return send_from_directory('index.html')

    @app.route('/flask_page', methods=['GET', 'POST'])
    def flask_page():
        return """<!doctype html><body><p>This page is being served by flask</p></body>"""

    socketio = SocketIO()
    socketio.init_app(app, async_mode='eventlet')
    return app


