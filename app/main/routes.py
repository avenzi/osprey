import os
import os.path
import re
import sys
import time
import logging
import mimetypes
import subprocess
import threading
import urllib.request
import json
import pytz

from datetime import datetime, timedelta
from random import seed, randint
from app import app, mysql, bcrypt
from app.views.forms import LoginForm, RegistrationForm
from flask import render_template, flash, redirect, url_for, Response, session, jsonify, request

# Views
from app.views.algorithm_view import AlgorithmView
from app.views.home_view import HomeView
from app.views.livefeed_view import LivefeedView
from app.views.login_view import LoginView
from app.views.registration_view import RegistrationView
from app.views.eventlog_view import EventlogView
from app.views.session_view import SessionView
from app.views.sense_view import SenseView

# Controllers
from app.controllers.login_controller import LoginController
from app.controllers.registration_controller import RegistrationController
from app.controllers.session_controller import SessionController
from app.controllers.livefeed_controller import LivefeedController
from app.controllers.algorithm_controller import AlgorithmController
from app.controllers.sense_controller import SenseController


LOG = logging.getLogger(__name__)
# Variable to disable logging in
global loginStatus
loginStatus = True # Avoid login for DECS -- should be false


@app.route('/', methods = ['GET','POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and LoginForm().validate_on_submit():
        return LoginController().handle_response()
    else:
        return LoginView().get_rendered_template()


@app.route('/home', methods=['GET'])
def home():
    return HomeView().get_rendered_template()


# TODO: refactor like how /login route was refactored (using RegistrationView and RegistrationController)
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST' and RegistrationForm().validate_on_submit():
        return RegistrationController().handle_response()
    else:
        return RegistrationView().get_rendered_template()


@app.route('/livefeed', methods=['GET', 'POST'])
def livefeed():
    if session.get('username') == True:
        return redirect(url_for('login'))

    if loginStatus != True:
        return redirect(url_for('login'))

    return LivefeedView().get_rendered_template()


@app.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    return SessionController().delete_session(session_id)


@app.route('/session/<int:session_id>')
def archived_session(session_id):
    return SessionView().serve_session(session_id)


@app.route('/livestream_config', methods=['GET', 'POST'])
def livestream_config():
    return LivefeedController().store_configuration(request.form)


@app.route('/update_sense', methods=['GET', 'POST'])
def update_sense():
    SenseController().monitor_sense_data()
    return SenseView().get_sense_data()


"""route is used to collect trigger settings from the live stream page"""
@app.route('/update_triggersettings', methods=['POST'])
def update_triggersettings():
    # Updating trigger settings in the session
    session['triggerSettings_temperature'] = request.form['temperature_input']
    session['triggerSettings_pressure'] = request.form['pressure_input']
    session['triggerSettings_humidity'] = request.form['humidity_input']

    return jsonify({'result' : 'success', 'temperature_input' : session.get('triggerSettings_temperature'), 
        'pressure_input' : session.get('triggerSettings_pressure'), 'humidity_input' : session.get('triggerSettings_humidity')})


"""route is used to retrieve items from the event log"""
@app.route('/retrieve_eventlog/<int:time>/<int:adjustment>/<int:mintime>', methods=['GET'])
def retrieve_eventlog(time, adjustment, mintime):
    # Instantiating an object that can execute SQL statements
    database_cursor = mysql.connection.cursor()

    # The id of the logged in user
    user_id = session.get('user_id')

    #Return the latest 15 event log entries for this user
    sql = """
        SELECT alert_message, alert_time
        FROM eventlog
        WHERE user_id = %s AND alert_time < %s AND alert_time > %s
        ORDER BY alert_time DESC
        LIMIT 15;
    """
    dt = datetime.fromtimestamp(time / 1000)
    dt = dt.astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
    dt_min = datetime.fromtimestamp(mintime / 1000)
    dt_min = dt_min.astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
    database_cursor.execute(sql, (user_id, dt, dt_min))
    results = database_cursor.fetchall()
    alerts = []
    for alert in results :
        alerts.append("{} at {}".format(alert[0], alert[1]))
    
    return render_template('snippets/eventlog_snippet.html', messages = alerts)

"""route is used to retrieve items from the event log"""
@app.route('/retrieve_sense/<int:time>/<int:adjustment>/<int:session_id>/<int:sensor_id>', methods=['GET'])
def retrieve_sense(time, adjustment, session_id, sensor_id):
    # Instantiating an object that can execute SQL statements
    database_cursor = mysql.connection.cursor()

    # Return the Sense Hat record closest in time to the time provided
    sql = """
        SELECT Temp, Press, Humid
        FROM Sense
        WHERE SessionId = %s and SensorId = %s AND Time < %s
        ORDER BY Time DESC
        LIMIT 1;
    """
    dt = datetime.fromtimestamp(time / 1000).astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
    database_cursor.execute(sql, (session_id, sensor_id, dt))
    result = database_cursor.fetchone()
    
    if result is None:
        return jsonify({})
    else:
        return jsonify({
            'temperature': result[0],
            'pressure': result[1],
            'humidity': result[2]
        })


@app.route('/videoframefetch/<frame>/<session>/<sensor>')
def videoframefetch(frame, session, sensor):
    frame = int(frame)
    sql = "SELECT * FROM VideoFrames WHERE SessionId = %s AND SensorId = %s AND %s BETWEEN FirstFrameNumber AND LastFrameNumber;"
    database_cursor = mysql.connection.cursor()
    database_cursor.execute(sql, (session, sensor, frame))

    frames_record = database_cursor.fetchone()
    last_frame_number = int(frames_record[4])
    frames_metadata = json.loads(frames_record[7])

    # TODO: test config changes
    response_frames = []
    frame_metadata = frames_metadata[frame]
    base_path = os.path.dirname(__file__) + '/../../data-ingestion'
    path = base_path + frame_metadata['path']
    with open(path, 'rb') as frame_file:
        response_frames.append(frame_file.read())
    
    response_bytes = b"".join(response_frames)
    response = Response(
        response_bytes,
        200,
        mimetype='image/jpeg',
        direct_passthrough=True,
    )
    response.headers.add('Accept-Ranges', 'bytes')

    return response


@app.route('/audiosegmentfetch/<timestamp>/<segment>/<session>/<sensor>')
def audiosegmentfetch(timestamp, segment, session, sensor):
    #print(timestamp)
    #print(segment)
    #print(session)
    #print(sensor)
    database_cursor = mysql.connection.cursor()

    timestamp = int(timestamp)
    segment = int(segment)

    # fetch on segment number
    segments_record = []
    if timestamp == -1:
        sql = "SELECT * FROM AudioSegments WHERE SessionId = %s AND SensorId = %s AND %s BETWEEN FirstSegmentNumber AND LastSegmentNumber;"
        database_cursor.execute(sql, (session, sensor, segment))
        segments_record = database_cursor.fetchone()
    elif segment == -1:
        pass
    
    print(segments_record)
    segments_metadata = json.loads(segments_record[7])
    base_path = os.path.dirname(__file__) + '/../../data-ingestion'
    segment_metadata = {}

    if timestamp == -1:
        # set timestamp in here
        segment_metadata = segments_metadata[str(segment)]
        timestamp = int(segment_metadata['time'])
    elif segment == -1:
        # set segment in here
        pass
    
    path = base_path + segment_metadata['path']

    response_bytes = bytes()
    with open(path, 'rb') as segment_file:
        response_bytes = segment_file.read()
    
    response = Response(
        response_bytes,
        200,
        mimetype='audio/mpeg',
        direct_passthrough=True,
    )

    response.headers.add('segment-number', segment)
    response.headers.add('segment-time', timestamp)

    return response


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
    #LOG.info('Requested: %s, %s', start, end)
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
    assert len(bytes) == length

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
    #LOG.info('Response: %s', response)
    #LOG.info('Response: %s', response.headers)
    return response


"""route is used to upload algorithms"""
@app.route("/algorithm_upload", methods=['GET', 'POST'])
def algorithm_upload():
    if request.method == 'POST':
        return AlgorithmController().handle_upload()
    elif request.method == 'GET':
        return AlgorithmView().get_uploads_snippet()


"""route is used for downloading boilerplate code"""
@app.route('/download_boilerplate')
def download_boilerplate():
    return AlgorithmController().download_boilerplate()


# TODO: move logic to AlgorithmController
"""route is used to handle uploaded algorithms"""
@app.route('/algorithm_handler', methods=['POST'])
def algorithm_handler():
    return AlgorithmController().handle_algorithm()