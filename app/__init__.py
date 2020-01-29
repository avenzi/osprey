from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)

#------------------------------------------
# Configure the database connection
#------------------------------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'CapstoneMySQLUser'
app.config['MYSQL_PASSWORD'] = 'CapstoneMySQLUserDbPw'
app.config['MYSQL_DB'] = 'CapstoneData'

# Establish connection to the database
mysql = MySQL(app)

from app.controllers import routes