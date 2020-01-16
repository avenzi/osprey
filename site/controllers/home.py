from flask import render_template
from main import app
# from main import mysql

@app.route("/")
def greeting():
    # Debug - works and creates a table if everything is configured correctly
    #database_cursor = mysql.connection.cursor()
    #database_cursor.execute('''CREATE TABLE test (id INTEGER, name VARCHAR(20))''')
    return render_template('home/start.html')

@app.route("/audio")
def audio():
    return render_template('audio/audio.html')
