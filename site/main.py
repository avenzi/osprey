from flask import Flask, render_template
from flask_mysqldb import MySQL

app = Flask(__name__, template_folder='templates')

#------------------------------------------
# Configure the database connection
#------------------------------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'CapstoneMySQLUser'
app.config['MYSQL_PASSWORD'] = 'CapstoneMySQLUserDbPw'
app.config['MYSQL_DB'] = 'CapstoneData'

# Establish the connection to the database
mysql = MySQL(app)

# Runs __init__.py in controllers module, which establishes all the routes
from controllers import *