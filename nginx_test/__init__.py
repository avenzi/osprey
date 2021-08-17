from flask import Flask, render_template
from flask_socketio import SocketIO


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__)

    @app.route('/index', methods=['GET', 'POST'])
    def index():
        return render_template('nginx_test/index.html')

    @app.route('/flask_page', methods=['GET', 'POST'])
    def flask_page():
        return """<!doctype html><body><p>This page is being served by flask</p></body>"""

    socketio = SocketIO()
    socketio.init_app(app, async_mode='eventlet')
    return app


