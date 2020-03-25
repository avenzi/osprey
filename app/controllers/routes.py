import os
import re
import sys
import time
import logging
import mimetypes
import subprocess
import threading
import urllib.request

from queue import Queue
from datetime import datetime
from random import seed, randint
from app import app, mysql, bcrypt
from app.controllers.video import *
from werkzeug.utils import secure_filename
from app.controllers.program import Program
from app.controllers.forms import LoginForm, TriggerSettingsForm, RegistrationForm
from app.controllers.data import Sense, Audio, EventLog
from flask import render_template, flash, redirect, url_for, Response, session, jsonify, request, send_file, send_from_directory

# BUFF_SIZE is the size of the number of bytes in each mp4 video chunk response
MB = 1 << 20
# Send 1 MB at a time
BUFF_SIZE = 1 * MB
# Seed used for random number generation
seed(1)
# global_start 
bytes_so_far = 0

# Data structure for handling audio data
audioData = Audio()
# Data structures for handling temperature data from two sense HATs
senseData1 = Sense()
senseData2 = Sense()
# Data structure for handling event log data
eventLogData = EventLog()

# Only .py files are allowed to be uploaded
ALLOWED_EXTENSIONS = set(['py'])
# Algorithms that are currently running for each user
runningAlgorithms = {}
# Dictionary of the latest ids associated to data types per username
eventLogEntryIds = {}

LOG = logging.getLogger(__name__)
global loginStatus
loginStatus = True # avoid login for DECS


@app.route('/', methods = ['GET','POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    database_cursor = mysql.connection.cursor()
    
    # The validate_on_submit() method does all form processing work and returns true when a form
    # is submitted and the browser sends a POST request indicating data is ready to be processed
    if form.validate_on_submit():
        database_cursor.execute("SELECT * FROM user where username = "+"'"+form.username.data+"'")

        myresult = database_cursor.fetchone()
        hashed_pw_from_db = myresult[2]
        user_input_pw = form.password.data
        correction_password = bcrypt.check_password_hash(hashed_pw_from_db, user_input_pw)

        if correction_password == False:
            redirect(url_for('login'))

        else:
            # Storing the username of a user in the session
            session['username'] = form.username.data
            global loginStatus
            loginStatus = True

            # Storing the id of the user that is logging in in the session
            database_cursor.execute("SELECT id FROM user WHERE username = "+"'"+session.get('username')+"'")
            session['user_id'] = database_cursor.fetchone()[0]

            # Creating session variables for the scalar trigger settings
            session['triggerSettings_audio'] = '' 
            session['triggerSettings_temperature'] = '' 
            session['triggerSettings_pressure'] = '' 
            session['triggerSettings_humidity'] = '' 

            # Creating the eventlog table if not already created. The eventlog table keeps track of all trigger events
            database_cursor.execute('''CREATE TABLE IF NOT EXISTS eventlog (id INTEGER UNSIGNED AUTO_INCREMENT, user_id INTEGER UNSIGNED, 
                alert_time DATETIME, alert_type VARCHAR(255), alert_message VARCHAR(255), PRIMARY KEY (id), FOREIGN KEY (user_id) REFERENCES user(id))''')

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
        # flash('registration requested for user {}, password={}, password_confirm={}'.format(
        #    form.username.data, form.password.data, form.password_confirm.data))

        if form.password.data != form.password_confirm.data:
            flash("Password confirmation and password need to be the same")
            return redirect(url_for('registration'))

        # Password Hashing
        inputted_password = form.password.data
        pw_hash = bcrypt.generate_password_hash(inputted_password).decode('utf-8')

        username = form.username.data

        database_cursor = mysql.connection.cursor()
        database_cursor.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER UNSIGNED AUTO_INCREMENT PRIMARY KEY , username VARCHAR(60), hashed_pw TEXT)''')
        database_cursor.execute(" INSERT INTO user (username,hashed_pw) VALUES ("+ '"'+ username +'"' + ","+ '"'+pw_hash +'"' +")")

        #INSERT INTO Persons (FirstName,LastName)
        #VALUES ('Lars','Monsn');
        # https://www.w3schools.com/python/python_mysql_select.asp

        mysql.connection.commit()

        return redirect(url_for('login'))
    return render_template('registration.html', title='Registration', form=form)


@app.route('/livefeed', methods=['GET', 'POST'])
def livefeed():
    if session.get('username') == True:
        return redirect(url_for('login'))

    if loginStatus != True:
        return redirect(url_for('login'))

    return render_template('livefeed.html', senseData1 = senseData1, senseData2 = senseData2, audioData = audioData)



    #def generate_video():
    #    with open("/root/capstone-site/site/static/video/107-8.mp4", "rb") as f:
    #        while True:
    #            chunk = ... # read each chunk or break if EOF
    #            yield chunk

    #return Response(stream_with_context(generate_video()), mimetype="video/mp4")


@app.route('/archives')
def archives():
    return archive(None)


@app.route('/archive/<int:archive_id>')
def archive(archive_id):
    if loginStatus != True:
        return redirect(url_for('login'))
    if archive_id == None:
        print("Archive id is None")
    else:
        print("archive_id: ", archive_id)

    if session.get('username') == True:
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




"""route is used to update Sense HAT values for the first Sense HAT in the live stream page"""
@app.route('/update_sense1', methods=['GET', 'POST'])
def update_sense1():
    senseData1.date = request.form['date']

    # Check if switch is on or off
    senseData1.status = request.form['status']
    if senseData1.status == 'OFF':
        senseData1.roomTemperature = "--.-"
        senseData1.airPressure = "--.-"
        senseData1.airHumidity = "--.-"

    else:
        try:
            # Set up Sense table connection
            database_cursor = mysql.connection.cursor()

            # get current Sense HAT data from DB
            database_cursor.execute("SELECT INET_NTOA(IP), Temp, Press, Humid FROM Sense WHERE IP <> INET_ATON('%s') ORDER BY Time DESC;" % senseData2.ip)
            ip, temp, press, humid = database_cursor.fetchone()


            # SQL command filters out senseData2's ip so no need to check for it
            if senseData1.ip == 0:
                senseData1.ip = ip
            
            
            # Convert to JQueryable objects
            senseData1.roomTemperature = "{:.2f}".format(temp)
            senseData1.airPressure = "{:.2f}".format(press)
            senseData1.airHumidity = "{:.2f}".format(humid)
        
        # Don't fail out if sense hat stream isn't working
        except Exception as e:
            print("Sense HAT 1 broken:", e)
            pass

    return jsonify({'result' : 'success', 'status' : senseData1.status, 'date' : senseData1.date, 'roomTemperature' : senseData1.roomTemperature,
    'airPressure': senseData1.airPressure, 'airHumidity': senseData1.airHumidity, 'ip' : senseData1.ip})


"""route is used to update Sense HAT values for the second Sense HAT in the live stream page"""
@app.route('/update_sense2', methods=['GET', 'POST'])
def update_sense2():
    senseData2.date = request.form['date']

    # Check if switch is on or off
    senseData2.status = request.form['status']
    if senseData2.status == 'OFF':
        senseData2.roomTemperature = "--.-"
        senseData2.airPressure = "--.-"
        senseData2.airHumidity = "--.-"

    else:
        # Set up Sense table connection
        database_cursor = mysql.connection.cursor()

        try:
            database_cursor.execute("SELECT INET_NTOA(IP), Temp, Press, Humid, Time FROM Sense WHERE IP <> INET_ATON('%s') ORDER BY Time DESC;" % senseData1.ip)
            ip, temp, press, humid, time = database_cursor.fetchone()

            # SQL command filters out senseData1's ip so no need to check for it
            if senseData2.ip == 0:
                senseData2.ip = ip


            senseData2.roomTemperature = "{:.2f}".format(temp)
            senseData2.airPressure = "{:.2f}".format(press)
            senseData2.airHumidity = "{:.2f}".format(humid)
        
        # Don't fail out of website on Sense HAT error
        except Exception as e:
            print("Sense HAT 2 broken:", e)
            pass

    return jsonify({'result' : 'success', 'status' : senseData2.status, 'date' : senseData2.date, 'roomTemperature' : senseData2.roomTemperature,
    'airPressure': senseData2.airPressure, 'airHumidity': senseData2.airHumidity, 'ip': senseData2.ip})


"""route is used to update audio values in the live stream page"""
@app.route('/update_audio', methods=['GET', 'POST'])
def update_audio():

    # Instantiating an object that can execute SQL statements
    database_cursor = mysql.connection.cursor()

    # The scalar trigger setting for audio
    triggerSettings_audio = session.get('triggerSettings_audio')
    # The id of the logged in user
    user_id = session.get('user_id')

    # Indicates whether audio has been turned on or not
    status = request.form['status']

    # The initial decibel level until set
    decibels = 0

    
    for _ in range(10):
        value = randint(0, 5)
        decibels = "6" + str(value)

    if (triggerSettings_audio != '') and (decibels > triggerSettings_audio):
        # Write audio data to database
        database_cursor.execute("INSERT INTO eventlog (user_id, alert_time, alert_type, alert_message) VALUES ('{}', NOW(), '{}', '{}');".format(user_id, "Audio", 
            "Audio exceeded " + triggerSettings_audio + " dB"))
        mysql.connection.commit()

    return jsonify({'result' : 'success', 'status' : status, 'decibels' : decibels})


"""route is used to collect trigger settings from the live stream page"""
@app.route('/update_triggersettings', methods=['POST'])
def update_triggersettings():
    # Updating trigger settings in the session
    session['triggerSettings_audio'] = request.form['audio_input']
    session['triggerSettings_temperature'] = request.form['temperature_input']
    session['triggerSettings_pressure'] = request.form['pressure_input']
    session['triggerSettings_humidity'] = request.form['humidity_input']

    return jsonify({'result' : 'success', 'audio_input' : session.get('triggerSettings_audio'), 'temperature_input' : session.get('triggerSettings_temperature'), 
        'pressure_input' : session.get('triggerSettings_pressure'), 'humidity_input' : session.get('triggerSettings_humidity')})


"""route is used to update the event log for all data types"""
@app.route('/update_eventlog', methods=['POST'])
def update_eventlog():

    # Instantiating an object that can execute SQL statements
    database_cursor = mysql.connection.cursor()

    # The username of the logged in user
    username = session.get('username')
    # The id of the logged in user
    user_id = session.get('user_id')

    # Indicates whether a trigger watch button is checked or not
    status = request.form['status']
    # Indicates whether a trigger watch button was just initially checked or has been checked
    initial = request.form['initial']
    # Indicates the data type associated with the trigger watch button
    data_type = request.form['data_type']


    if status == 'ON':
    
        # Trigger watch button was just initially checked
        if initial == 'YES':

            # eventLogEntryIds is a global dictionary of the latest ids associated to data types per username
            if username not in eventLogEntryIds:
    
                # Check to see if the user has any previous entries in the eventlog table for the specified data type
                database_cursor.execute("SELECT max(id) FROM eventlog WHERE user_id = '%s' AND alert_type = '%s';" % (user_id, data_type))
                entryId = database_cursor.fetchone()

                #  If there is an previous entry in the eventlog table
                if len(entryId) != 0:
                    eventLogEntryIds[username] = {data_type : entryId[0]}

                # If there are no previous entries in the eventlog table
                else:
                    eventLogEntryIds[username] = {data_type : 0}

            else:
                # If the user has previous entries in the eventlog table for the specified data type, set the latest eventlog entry id for that datatype
                database_cursor.execute("SELECT max(id) FROM eventlog WHERE user_id = '%s' AND alert_type = '%s';" % (user_id, data_type))
                entryId = database_cursor.fetchone()[0]
                eventLogEntryIds[username][data_type] = entryId

        # Trigger watch button has already been checked initially
        else:
            # Fetching the newest alert data
            database_cursor.execute("SELECT id, alert_time, alert_type, alert_message FROM eventlog WHERE user_id = '{}' AND alert_type = '{}' AND id > '{}';".format(user_id, data_type, eventLogEntryIds[username][data_type]))
            entrysToAdd = database_cursor.fetchall()

            alerts = []

            # Create a list of messages to ship off
            for entry in entrysToAdd:
                alert = entry[2] + " Trigger: " + entry[3] + " @ " + str(entry[1])
                alerts.append(alert)

            # Set the latest eventlog entry id for the specified data type
            database_cursor.execute("SELECT max(id) FROM eventlog WHERE user_id = '%s' AND alert_type = '%s';" % (user_id, data_type))
            entryId = database_cursor.fetchone()[0]
            eventLogEntryIds[username][data_type] = entryId

            return render_template('snippets/eventlog_snippet.html', messages = alerts)

    return jsonify({'result' : 'success'})




@app.route('/test', methods=['GET'])
def test():
    return render_template('test.html')


@app.route('/testshaka', methods=['GET'])
def testshaka():
    return render_template('test-shaka.html')


@app.route('/testvideo', methods=['GET'])
def testvideo():
    return render_template('test-video.html')


@app.route('/testaudio', methods=['GET'])
def testaudio():
    return render_template('test-audio.html')

@app.route("/dashvideo", methods=['GET'])
def dashvideo():
    path = "/var/www/html/video3/output-dash.mpd"
    return partial_response(path, 0, BUFF_SIZE, None)


""" .mpd, then init.mp4, then .m4s segments after that """
@app.route('/filefetch/<filename>')
def filefetch(filename):
    print("filename requested: " + filename)

    # could construct a master.mpd here if this is an archive viewing (or just make it during livestream)
    path = "/var/www/html/audio/" + filename
    return partial_response(path, 0, os.path.getsize(path), None)


@app.route('/filefetchvideo/<filename>')
def filefetchvideo(filename):
    print("filename requested: " + filename)

    # could construct a master.mpd here if this is an archive viewing (or just make it during livestream)
    path = "/var/www/html/video/dash-segments/" + filename
    return partial_response(path, 0, os.path.getsize(path), None)


@app.route('/filefetchaudio/<filename>')
def filefetchaudio(filename):
    print("filename requested: " + filename)

    path = "/var/www/html/audio/mp3-segments/" + filename

    if os.path.exists(path):
        return partial_response(path, 0, os.path.getsize(path), None) # return the whole file at once
    else:
        return jsonify({'nodata': True})

@app.route('/fetchvideo', methods=['GET'])
def fetchvideo():
    print("FETCHING VIDEO")
    path = "/root/capstone-site/site/static/video/107-6.mp4"
    #start, end = get_range(request)
    #return partial_response(path, start, end)
    return partial_response(path, 0, BUFF_SIZE, None)


def get_range(request):
    range = request.headers.get('Range')
    LOG.info('Requested: %s', range)
    m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None


def partial_response(path, start, buff_size, end=None):
    LOG.info('Requested: %s, %s', start, end)
    file_size = os.path.getsize(path)

    # Determine (end, length)
    if end is None:
        end = start + buff_size - 1
    end = min(end, file_size - 1)
    end = min(end, start + buff_size - 1)
    end = file_size - 1
    length = end - start + 1

    # start is the bytes number requested by the browser
    # Read file
    with open(path, 'rb') as fd:
        fd.seek(start)
        bytes = fd.read(length)
        print("len(bytes): " + str(len(bytes)))
        print(buff_size)
    assert len(bytes) == length

    if len(bytes) < buff_size: # if last read on an image
        # send the first chunk of the next image
        pass

    response = Response(
        bytes,
        200,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True,
    )
    response.headers.add(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            #start, end, file_size,
            start, end, file_size,
        ),
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'
    )
    LOG.info('Response: %s', response)
    LOG.info('Response: %s', response.headers)
    return response




"""route is used for downloading boilerplate code"""
@app.route('/downloadBoilerplate')
def downloadBoilerplate():
    return send_from_directory(directory=app.config['DOWNLOADS_FOLDER'], filename="boilerplate.py", as_attachment=True)


"""route is used to upload algorithms"""
@app.route("/algorithm_upload", methods=['GET', 'POST'])
def algorithm_upload():
    files = []
    username = session.get('username')

    # Creating a username in runningAlgorithms if it does not exist
    if username not in runningAlgorithms:
        runningAlgorithms[username] = {}

    # Creating an uploads folder for a user if one does not already exist
    if not os.path.exists(os.path.join(app.config['UPLOADS_FOLDER'], username)):
        os.makedirs(os.path.join(app.config['UPLOADS_FOLDER'], username))

    if request.method == 'POST':
        # Checking that the post request has the file part
        if 'file' not in request.files:
            return jsonify({'result' : 'No File Part'})

        file = request.files['file']

        # Checking that a file was selected
        if file.filename == '':
            return jsonify({'result' : 'No File Selected'})

        # Ensuring that the file name has an extension that is allowed
        if file and ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOADS_FOLDER'], username, filename))
            # Getting a list of all files in the uploads directory
            with os.scandir(os.path.join(app.config['UPLOADS_FOLDER'], username)) as entries:
                for entry in entries:
                    if entry.is_file():
                        files.append(entry.name)
            return render_template('snippets/uploads_list_snippet.html', files = files, runningAlgorithms = runningAlgorithms[username])

        return jsonify({'result' : 'File Extension Not Allowed'})

    elif request.method == 'GET':
        # Getting a list of all files in the uploads directory
        with os.scandir(os.path.join(app.config['UPLOADS_FOLDER'], username)) as entries:
            for entry in entries:
                if entry.is_file():
                    files.append(entry.name)
        return render_template('snippets/uploads_list_snippet.html', files = files, runningAlgorithms = runningAlgorithms[username])


"""route is used to handle uploaded algorithms"""
@app.route('/algorithm_handler', methods=['POST'])
def algorithm_handler():
    files = []
    database_cursor = mysql.connection.cursor()
    filename = request.form['filename'] + ".py"
    buttonPressed = request.form['button']
    username = session.get('username')
    user_id = session.get('user_id')

    # Creating a username in runningAlgorithms if it does not exist
    if username not in runningAlgorithms:
        runningAlgorithms[username] = {}

    if buttonPressed == "select":
        if filename not in runningAlgorithms[username]:
            #  Pass the filename, id, and username of the user into the thread
            program_thread = Program(Queue(), args=(True, filename, user_id, username))

            program_thread.start()
            runningAlgorithms[username][filename] = program_thread
            print("Algorithms running: " + str(runningAlgorithms))

            # Getting a list of all files in the uploads directory
            with os.scandir(os.path.join(app.config['UPLOADS_FOLDER'], username)) as entries:
                for entry in entries:
                    if entry.is_file():
                        files.append(entry.name)
            return render_template('snippets/uploads_list_snippet.html', files = files, runningAlgorithms = runningAlgorithms[username])

        elif filename in runningAlgorithms[username]:
            # Exiting the thread
            runningAlgorithms[username][filename].stop()
            
            # Deleting thread from runningAlgorithms
            # FOR DEBUGGING: Comment this line out to see if the thread truly stopped
            del runningAlgorithms[username][filename]

            print("Algotithms running: " + str(runningAlgorithms))

            # Getting a list of all files in the uploads directory
            with os.scandir(os.path.join(app.config['UPLOADS_FOLDER'], username)) as entries:
                for entry in entries:
                    if entry.is_file():
                        files.append(entry.name)
            return render_template('snippets/uploads_list_snippet.html', files = files, runningAlgorithms = runningAlgorithms[username])

    elif buttonPressed == "view":
        f = open(os.path.join(app.config['UPLOADS_FOLDER'], username, filename), "r")
        content = f.read()
        f.close()
        return render_template('snippets/uploads_view_snippet.html', content = content, filename = filename)

    elif buttonPressed == "delete":
        # If a file is deleted, delete from running algorithms as well
        if filename in runningAlgorithms[username]:
            del runningAlgorithms[username][filename]

        with os.scandir(os.path.join(app.config['UPLOADS_FOLDER'], username)) as entries:
            for entry in entries:
                if entry.is_file() and (entry.name == filename):
                    os.remove(os.path.join(app.config['UPLOADS_FOLDER'], username, filename))
                else:
                    files.append(entry.name)  

        return render_template('snippets/uploads_list_snippet.html', files = files, runningAlgorithms = runningAlgorithms[username])

    return jsonify({'result' : 'Button Not Handled'})