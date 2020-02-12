from flask import render_template, flash, redirect, url_for, Response
from app import app
from app.controllers.forms import LoginForm, TriggerSettingsForm, RegistrationForm
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
        database_cursor = mysql.connection.cursor()
        database_cursor.execute("SELECT * FROM user where username = "+"'"+form.username.data+"'")
        myresult = database_cursor.fetchone()
        hashed_pw_from_db = myresult[2]
        user_input_pw = form.password.data
        correction_password = bcrypt.check_password_hash(hashed_pw_from_db, user_input_pw)
        if correction_password == False:
            flash("Wrong password")
            redirect(request.url)
       #     return redirect(url_for('livefeed'))
        else:
            flash("login password work")
            return redirect(url_for('livefeed'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/home')
def home():
    
    return render_template('home.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    form = RegistrationForm()
    #-------------------------------------------------------------------------------------------
    # The validate_on_submit() method does all form processing work and returns true when a form
    # is submitted and the browser sends a POST request indicating data is ready to be processed
    #-------------------------------------------------------------------------------------------
    if form.validate_on_submit():
        # A template in the application is used to render flashed messages that Flask stores
        flash('registration requested for user {}, password={}, password_confirm={}'.format(
            form.username.data, form.password.data, form.password_confirm.data))

        if form.password.data != form.password_confirm.data:
            flash("Password confirmation and password need to be the same")
            return redirect(url_for('registration'))

        # password hashing
        inputted_password = form.password.data
        pw_hash = bcrypt.generate_password_hash(inputted_password).decode('utf-8')

        username = form.username.data

        database_cursor = mysql.connection.cursor()
        database_cursor.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER UNSIGNED AUTO_INCREMENT PRIMARY KEY , username VARCHAR(60), hashed_pw VARCHAR(64))''')
        database_cursor.execute(" INSERT INTO user (username,hashed_pw) VALUES ("+ '"'+ username +'"' + ","+ '"'+pw_hash +'"' +")")


        #INSERT INTO Persons (FirstName,LastName)
        #VALUES ('Lars','Monsn');
        # https://www.w3schools.com/python/python_mysql_select.asp

        mysql.connection.commit()


        #saving to database
        # write user, pw_hash to database

        return redirect(url_for('login'))
    return render_template('registration.html', title='Registration', form=form)

@app.route('/livefeed', methods=['GET', 'POST'])
def livefeed():
    form = TriggerSettingsForm()
    if form.validate_on_submit():
        return 'Success!'
    return render_template('livefeed.html', form=form)

@app.route('/archives')
def archives():
    return render_template('archives.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')