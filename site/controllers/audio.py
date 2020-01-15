from flask import render_template
from main import app

@app.route("/audio")
def index():
    return render_template('audio/audio.html')
