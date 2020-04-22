from flask import Flask, session
from config import Config
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.config["SECRET_KEY"] = "youmayneedtoguess"

# Updating Flask configuration using created Config class
app.config.from_object(Config)

# Establish connection to the database
mysql = MySQL(app)

# Initializing Flask-Bootstrap
bootstrap = Bootstrap(app)

from app.main import routes