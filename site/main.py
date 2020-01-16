import os
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__, template_folder='templates')

socketio = SocketIO(app)

# Runs __init__.py in controllers module, which establishes all the routes
from controllers import *