from flask import render_template, flash, redirect, url_for, Response
from app import app
from app.controllers.forms import LoginForm
from app.controllers.video import *
from app import mysql
from app import bcrypt


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    #-------------------------------------------------------------------------------------------
    # The validate_on_submit() method does all form processing work and returns true when a form
    # is submitted and the browser sends a POST request indicating data is ready to be processed
    #-------------------------------------------------------------------------------------------
    if form.validate_on_submit():
        # A template in the application is used to render flashed messages that Flask stores
        flash('Login requested for user {}, remember_me={}, password_input={}'.format(
            form.username.data, form.remember_me.data, form.password.data))
        
        # 1. check DB for user .. if not user in DB, return error
        #hashed_pw_from_db = get_via_sql
        #user_input_pw = form.password.data
        #correct_password = bcrypt.check_password_hash(hashed_pw_from_db, user_input_pw))

        temp_user = 'Lianghao'
        temp_password = '123'
        flash("login")
        if form.username.data == temp_user and form.password.data == temp_password:
            flash("login password work")
            return redirect(url_for('livefeed'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/home')
def home():

    return render_template('home.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    form = LoginForm()
    #-------------------------------------------------------------------------------------------
    # The validate_on_submit() method does all form processing work and returns true when a form
    # is submitted and the browser sends a POST request indicating data is ready to be processed
    #-------------------------------------------------------------------------------------------
    if form.validate_on_submit():
        # A template in the application is used to render flashed messages that Flask stores
        flash('registration requested for user {}, remember_me={}, password_input={}'.format(
            form.username.data, form.remember_me.data, form.password.data))

        # password hashing
        inputted_password = form.password.data
        pw_hash = bcrypt.generate_password_hash(inputted_password)
        flash("works?: {}".format(bcrypt.check_password_hash(pw_hash, inputted_password))) # returns True

        database_cursor = mysql.connection.cursor()
        database_cursor.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTO_INCREMENT, username VARCHAR(20), hashed_pw VARCHAR(20))''')

        # https://www.w3schools.com/python/python_mysql_select.asp

        mysql.connection.commit()


        #saving to database
        # write user, pw_hash to database

        return redirect(url_for('login'))
    return render_template('registration.html', title='Registration', form=form)

@app.route('/livefeed')
def livefeed():
    return render_template('livefeed.html')

@app.route('/archives')
def archives():
    return render_template('archives.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')