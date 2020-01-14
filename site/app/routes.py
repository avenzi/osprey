from flask import render_template, flash, redirect
from app import app
from app.forms import StartForm

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = StartForm()
    if form.validate_on_submit():
        flash('Start recording')
        return redirect('/recording')
    return render_template('start.html', form=form)

@app.route('/recording')
def record():
    return "Recording Placeholder"
