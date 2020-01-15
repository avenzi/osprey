from flask import render_template
from main import app
from . import audio as audio

@app.route("/")
def greeting():
    return render_template('home/start.html', var=audio.index())

