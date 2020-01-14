from flask import Flask, render_template

app = Flask(__name__, template_folder='templates')

# Runs __init__.py in controllers module, which establishes all the routes
from controllers import *