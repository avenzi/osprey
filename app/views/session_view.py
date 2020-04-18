from app.views.view import View

import json
from datetime import datetime

class SessionView(View):
    def serve_session(self, session_id):
        # Retrieve the most recent recorded Sessions
        self.database_cursor.execute("""SELECT id, StartDate FROM Session ORDER BY StartDate DESC LIMIT 5;""")
        sessions_result = self.database_cursor.fetchall()
        
        session_id = session_id if session_id != None else -1
        sql = """SELECT id, Name, INET_NTOA(IP), SessionId, SensorType FROM SessionSensor WHERE SessionId = %s;"""
        self.database_cursor.execute(sql, (session_id,))
        session_sensors = self.database_cursor.fetchall()

        session_sensors_serialized = json.dumps(session_sensors, separators=(',', ':'))
        #print(session_sensors_serialized)

        session_start_time = -1
        session_end_time = -1
        sql = """SELECT id, StartDate, EndDate FROM Session WHERE StartDate = (SELECT MAX(StartDate) FROM Session);"""
        self.database_cursor.execute(sql)
        session_info = self.database_cursor.fetchone()
        if session_id != -1:
            epoch = datetime.utcfromtimestamp(0)
            session_start_time = int((session_info[1] - epoch).total_seconds() * 1000.0) + 1000
            session_end_time = int((session_info[2] - epoch).total_seconds() * 1000.0) - 1000

        cameras = []
        microphones = []
        sense_hats = []
        for session_sensor in session_sensors:
            sensor_type = session_sensor[4]
            sensor_name = session_sensor[1]

            if sensor_type == 'PiCamera':
                sql = """SELECT LastFrameNumber FROM VideoFrames WHERE FirstFrameTimestamp = (SELECT MAX(FirstFrameTimestamp) FROM VideoFrames WHERE SensorId = %s);"""
                self.database_cursor.execute(sql, (session_sensor[0],))
                result = self.database_cursor.fetchone()
                last_frame_number = 0
                if result:
                    last_frame_number = result[0]

                camera_view_data = dict(
                    sensor_id = session_sensor[0],
                    sensor_type = sensor_type,
                    last_frame_number = last_frame_number,
                    name = sensor_name
                )
                cameras.append(camera_view_data)
            elif sensor_type == 'Microphone':
                mic_view_data = dict(
                    sensor_id = session_sensor[0],
                    sensor_type = sensor_type,
                    name = sensor_name
                )
                microphones.append(mic_view_data)
            elif sensor_type == "SenseHat":
                sense_view_data = dict(
                    sensor_id = session_sensor[0],
                    sensor_type = sensor_type,
                    name = sensor_name
                )
                sense_hats.append(sense_view_data)
        
        print("Sense Hats:")
        print(sense_hats)

        sensor_selections = []
        list_index = 1
        for sensor in (cameras + microphones + sense_hats):
            sensor_selections.append(dict(
                sensor_id = sensor['sensor_id'],
                sensor_type = sensor['sensor_type'],
                sensor_name = sensor['name'],
                index = list_index
            ))
            list_index = list_index + 1
        
        print("Sensor selections")
        print(sensor_selections)

        return self.render('archives.html',
            session_id = session_id,
            session_sensors_serialized = session_sensors_serialized,
            session_start_time = session_start_time,
            session_end_time = session_end_time,
            cameras = cameras,
            microphones = microphones,
            sense_hats = sense_hats,
            sensor_selections = sensor_selections
        )

