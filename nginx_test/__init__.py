from flask import Flask


def create_app():
    """ Application factory to create the app and be passed to workers """
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'thisisthesecretkeyfortheflaskserver'

    """
    # add basic favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # serve static js files
    @app.route('/js/<filename>')
    def serve_js(filename):
        return send_from_directory(os.path.join(app.root_path, 'static', 'js'), filename)
    """

    @app.route('/index', methods=['GET', 'POST'])
    def index():
        return """<!doctype html><body><p>Hello World</p></body>"""

    from app.main import socketio
    socketio.init_app(app, async_mode='eventlet')
    return app


