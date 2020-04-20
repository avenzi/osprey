from app.views.view import View

from flask import request, session, jsonify

class SenseView(View):
    def get_sense_data(self):
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

            # Convert to JQueryable objects
            roomTemperature = "{:.2f}".format(temp)
            airPressure = "{:.2f}".format(press)
            airHumidity = "{:.2f}".format(humid)
        except Exception as e:
            pass
        
        return jsonify({'roomTemperature' : roomTemperature, 'airPressure': airPressure, 'airHumidity': airHumidity})
