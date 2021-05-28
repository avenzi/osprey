from flask import Blueprint
from flask_socketio import SocketIO

# define blueprints
auth = Blueprint('auth', __name__, url_prefix='/auth')
streams = Blueprint('streams', __name__)

# Flask-SocketIO object to send and receive messages
socketio = SocketIO()

# these are imported below to avoid recursive imports when importing the above objects

# import routes/events associated with these blueprints/socket
from app.main import auth_routes, stream_routes, events, EEG_stream