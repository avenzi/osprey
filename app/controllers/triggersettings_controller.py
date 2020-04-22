from app.controllers.controller import Controller

from flask import request, jsonify, session

class TriggerSettingsController(Controller):

    def update_triggersettings(self):
        # Updating trigger settings in the session
        session["triggerSettings_temperature"] = request.form["temperature_input"]
        session["triggerSettings_pressure"] = request.form["pressure_input"]
        session["triggerSettings_humidity"] = request.form["humidity_input"]

        return jsonify({"temperature_input" : session.get("triggerSettings_temperature"), "pressure_input" : session.get("triggerSettings_pressure"), 
            "humidity_input" : session.get("triggerSettings_humidity")})