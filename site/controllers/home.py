from flask import render_template
from main import app

@app.route("/")
def greeting():
    return render_template('home/start.html', var=None)