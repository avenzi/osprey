from flask import Flask
from config import Config
from flask_mysqldb import MySQL

app = Flask(__name__)

# Updating Flask configuration using created Config class
app.config.from_object(Config)

# Establish connection to the database
mysql = MySQL(app)

from app.controllers import routes