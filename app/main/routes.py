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
from app.controllers.triggersettings_controller import TriggerSettingsController
from app.controllers.video_controller import VideoController
from app.controllers.audio_controller import AudioController


LOG = logging.getLogger(__name__)
# Variable to disable logging in
global loginStatus
loginStatus = True # Avoid login for DECS -- should be false


@app.route("/", methods = ["GET","POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and LoginForm().validate_on_submit():
        return LoginController().handle_response()
    else:
        return LoginView().get_rendered_template()

@app.route("/home", methods=["GET"])
def home():
    return HomeView().get_rendered_template()

@app.route("/registration", methods=["GET", "POST"])
def registration():
    if request.method == "POST" and RegistrationForm().validate_on_submit():
        return RegistrationController().handle_response()
    else:
        return RegistrationView().get_rendered_template()


@app.route("/livefeed", methods=["GET", "POST"])
def livefeed():
    if session.get("username") == True:
        return redirect(url_for("login"))

    if loginStatus != True:
        return redirect(url_for("login"))

    return LivefeedView().get_rendered_template()


@app.route("/delete_session/<int:session_id>", methods=["POST"])
def delete_session(session_id):
    return SessionController().delete_session(session_id)


@app.route("/session/<int:session_id>")
def archived_session(session_id):
    return SessionView().serve_session(session_id)


@app.route("/livestream_config", methods=["GET", "POST"])
def livestream_config():
    return LivefeedController().store_configuration(request.form)


@app.route("/update_sense", methods=["GET", "POST"])
def update_sense():
    SenseController().monitor_sense_data()
    return SenseView().get_most_recent_sense_data()


"""route is used to collect trigger settings from the live stream page"""
@app.route("/update_triggersettings", methods=["POST"])
def update_triggersettings():
    return TriggerSettingsController().update_triggersettings()


"""route is used to retrieve items from the event log"""
@app.route("/retrieve_eventlog/<int:time>/<int:adjustment>/<int:mintime>", methods=["GET"])
def retrieve_eventlog(time, adjustment, mintime):
    return EventlogView().get_closest_items(time, adjustment, mintime)


"""route is used to retrieve items from the event log"""
@app.route("/retrieve_sense/<int:time>/<int:adjustment>/<int:session_id>/<int:sensor_id>", methods=["GET"])
def retrieve_sense(time, adjustment, session_id, sensor_id):
    return SenseView().get_by_time(time, adjustment, session_id, sensor_id)


@app.route("/videoframefetch/<frame>/<session>/<sensor>")
def videoframefetch(frame, session, sensor):
    return VideoController().serve_frame(int(frame), session, sensor)


@app.route("/audiosegmentfetch/<timestamp>/<segment>/<session>/<sensor>")
def audiosegmentfetch(timestamp, segment, session, sensor):
    return AudioController().serve_segment(int(timestamp), int(segment), session, sensor)


"""route is used to upload algorithms"""
@app.route("/algorithm_upload", methods=["GET", "POST"])
def algorithm_upload():
    if request.method == "POST":
        return AlgorithmController().handle_upload()
    elif request.method == "GET":
        return AlgorithmView().get_uploads_snippet()


"""route is used for downloading boilerplate code"""
@app.route("/download_boilerplate")
def download_boilerplate():
    return AlgorithmController().download_boilerplate()


"""route is used to handle uploaded algorithms"""
@app.route("/algorithm_handler", methods=["POST"])
def algorithm_handler():
    return AlgorithmController().handle_algorithm()