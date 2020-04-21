from app.views.view import View

from datetime import datetime, timedelta
from flask import request, session, jsonify
import pytz

class SenseView(View):
    def get_by_time(self, time, adjustment, session_id, sensor_id):
        data = {}

        # Return the Sense record closest in time to the time provided
        sql = """
            SELECT Temp, Press, Humid
            FROM Sense
            WHERE SessionId = %s and SensorId = %s AND Time < %s
            ORDER BY Time DESC
            LIMIT 1;
        """
        dt = datetime.fromtimestamp(time / 1000).astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
        self.database_cursor.execute(sql, (session_id, sensor_id, dt))
        result = self.database_cursor.fetchone()
        
        if result is not None:
            data = {
                'temperature': result[0],
                'pressure': result[1],
                'humidity': result[2]
            }
        
        return jsonify(data)

    def get_most_recent_sense_data(self):
        # The IP Address of the Sense HAT
        ip = request.form['ip']

        # The initial measurements until set
        roomTemperature = 0
        airPressure = 0
        airHumidity = 0

        try:
            sql = """
                SELECT Temp, Press, Humid
                FROM Sense
                WHERE IP = INET_ATON(%s)
                ORDER BY Time DESC;
            """

            # Get current Sense HAT data from DB
            self.database_cursor.execute(sql, (ip,))
            temp, press, humid = self.database_cursor.fetchone()

            # Convert the values to compatible objects that with fixed decimal places
            roomTemperature = "{:.2f}".format(temp)
            airPressure = "{:.2f}".format(press)
            airHumidity = "{:.2f}".format(humid)
        except Exception as e:
            pass
        
        return jsonify({'roomTemperature' : roomTemperature, 'airPressure': airPressure, 'airHumidity': airHumidity})
