from flask import render_template, flash, redirect, url_for, Response, session, jsonify
from app import app
from app.controllers.forms import LoginForm, TriggerSettingsForm, RegistrationForm
from app.controllers.video import *
#from app.controllers.receiver import *
from app.controllers.data import *
from app import mysql
from app import bcrypt
from datetime import datetime

from random import seed
from random import randint

seed(1)

global loggined

loggined = False


@app.route('/', methods = ['GET','POST'])
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
            redirect(url_for('login'))
       #     return redirect(url_for('livefeed'))
        else:
            flash("login password work")
            session['user'] = form.username.data
            loggined = True
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
    if session.get('user') == True:
        return redirect(url_for('login'))

    if loggined != True:
        return redirect(url_for('login'))

    form = TriggerSettingsForm()
    # new temperature data object
    temperatureData = Temperature()    
    if form.validate_on_submit():
        return 'Success!'
    return render_template('livefeed.html', form=form, temperatureData = temperatureData)

@app.route('/archives')
def archives():
    return archive(None)

@app.route('/archive/<int:archive_id>')
def archive(archive_id):
    if loggined != True:
        return redirect(url_for('login'))
    if archive_id == None:
        print("Archive id is None")
    else:
        print("archive_id: ", archive_id)

    if session.get('user') == True:
        return redirect(url_for('login'))
    
    # what are the recent recorded sessions
    database_cursor = mysql.connection.cursor()
    database_cursor.execute("""SELECT id, StartDate FROM Session ORDER BY StartDate DESC LIMIT 5;""")
    db_result = database_cursor.fetchall()

    template_data = []
    if db_result != None:
        for session_data in db_result:
            template_data.append(dict(
                id = session_data[0],
                time = session_data[1].strftime("%m/%d/%Y @ %H:%M:%S")
            ))
    
    print("Template data:")
    print(template_data)

    return render_template('archives.html', 
        sessions=template_data,
        session_id= (archive_id if archive_id != None else -1))

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera(-1, False)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/session_feed/<int:session_id>')
def session_feed(session_id):
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera(session_id, True)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

"""route is used to start the live stream"""
@app.route('/start')
def start():
    write_token("START")
    print("pressed Start")
    return {}

"""route is used to stop the live stream"""
@app.route('/stop')
def stop():
    print("pressed Stop")
    write_token("STOP")
    return {}

def write_token(token_value):
    database_cursor = mysql.connection.cursor()
    database_cursor.execute("""CREATE TABLE IF NOT EXISTS `Token` (id int(11) NOT NULL AUTO_INCREMENT, Value TEXT NOT NULL, PRIMARY KEY (id));""")
    mysql.connection.commit()

    # insert new token
    sql = "INSERT INTO `Token` (`Value`) VALUES (%s)"
    database_cursor.execute(sql, (token_value,))
    mysql.connection.commit()

"""route is used to update sensor values in the live stream page"""
@app.route('/update_sense', methods=['GET'])
def update_sense():
    temperatureData = Temperature()

    for _ in range(10):
        value = randint(0, 97)
        temperatureData.roomTemperature = str(value) + ".0"
        temperatureData.skinTemperatureSub1 = str(value+1) + '.0'
        temperatureData.skinTemperatureSub2 = str(value+2) + '.0'

    return jsonify({'result' : 'success', 'roomTemperature' : temperatureData.roomTemperature, 'skinTemperatureSub1' : temperatureData.skinTemperatureSub1, 
        'skinTemperatureSub2' : temperatureData.skinTemperatureSub2})

