from app.controllers.controller import Controller

from flask import Response, jsonify
import json
import pytz
from datetime import datetime

class LivefeedController(Controller):
    def store_configuration(self, form):
        config_tokens = form["livestream_config"].split("&")
        config_json = {
            "cameras": [],
            "microphones": [],
            "sense_hats": []
        }

        if len(form["livestream_config"]) == 0:
            return jsonify()

        index = 0
        for token in config_tokens:
            key = token.split("=")[0]
            value = token.split("=")[1].replace("%20", " ")

            if "cam-ip-input" in token:
                name = config_tokens[index + 1].split("=")[1].replace("%20", " ")

                metadata = {"name": name, "ip": value}
                config_json["cameras"].append(metadata)
            elif "mic-ip-input" in token:
                name = config_tokens[index + 1].split("=")[1].replace("%20", " ")
                metadata = {"name": name, "ip": value}
                config_json["microphones"].append(metadata)
            elif "sen-ip-input" in token:
                name = config_tokens[index + 1].split("=")[1].replace("%20", " ")
                metadata = {"name": name, "ip": value}
                config_json["sense_hats"].append(metadata)

            index = index + 1
        
        compacted_json = json.dumps(config_json, separators=(",", ":"))
        # Instantiating an object that can execute SQL statements
        self.database_cursor.execute("""SELECT id FROM Session WHERE id = (SELECT MAX(id) FROM Session)""")
        result = self.database_cursor.fetchone()
        session_id = 1 if result == None else result[0] + 1

        for metadata in config_json["cameras"]:
            ip = metadata["ip"]
            name = metadata["name"]
            sql = "INSERT INTO SessionSensor (`IP`, `Name`, `SessionId`, `SensorType`) VALUES (INET_ATON(%s), %s, %s, %s);"
            self.database_cursor.execute(sql, (ip, name, session_id, "PiCamera"))
        
        for metadata in config_json["microphones"]:
            ip = metadata["ip"]
            name = metadata["name"]
            sql = "INSERT INTO SessionSensor (`IP`, `Name`, `SessionId`, `SensorType`) VALUES (INET_ATON(%s), %s, %s, %s);"
            self.database_cursor.execute(sql, (ip, name, session_id, "Microphone"))
        
        for metadata in config_json["sense_hats"]:
            ip = metadata["ip"]
            name = metadata["name"]
            sql = "INSERT INTO SessionSensor (`IP`, `Name`, `SessionId`, `SensorType`) VALUES (INET_ATON(%s), %s, %s, %s);"
            self.database_cursor.execute(sql, (ip, name, session_id, "SenseHat"))

        
        dt = datetime.now().astimezone(pytz.timezone("America/Detroit"))
        sql = "INSERT INTO Session (`StartDate`, `SensorConfig`) VALUES (%s, %s);"
        self.database_cursor.execute(sql, (dt, compacted_json))
        self.database_connection.commit()

        sql = "SELECT id, INET_NTOA(IP), SessionId, SensorType FROM SessionSensor WHERE SessionId = %s"
        self.database_cursor.execute(sql, (session_id,))
        session_sensors = self.database_cursor.fetchall()

        return jsonify(session_sensors)