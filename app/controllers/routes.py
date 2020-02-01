from flask import render_template, flash, redirect, url_for
from app import app
from app.controllers.forms import LoginForm

@app.route('/')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    #-------------------------------------------------------------------------------------------
    # The validate_on_submit() method does all form processing work and returns true when a form
    # is submitted and the browser sends a POST request indicating data is ready to be processed
    #-------------------------------------------------------------------------------------------
    if form.validate_on_submit():
        # A template in the application is used to render flashed messages that Flask stores
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/livefeed')
def livefeed():
    return render_template('livefeed.html')

@app.route('/archives')
def archives():
    return render_template('archives.html')