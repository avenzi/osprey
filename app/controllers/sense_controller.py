from flask import request, session

from app.controllers.controller import Controller

class SenseController(Controller):
    def monitor_sense_data(self):
        # The IP Address of the Sense HAT
        ip = request.form['ip']

        # The name of the Sense HAT
        name = request.form['name'].replace("%20", " ")

        # The scalar trigger settings for temperature, pressure, and humidity
        triggerSettings_temperature = session.get('triggerSettings_temperature')
        triggerSettings_pressure = session.get('triggerSettings_pressure')
        triggerSettings_humidity = session.get('triggerSettings_humidity')

        # The id of the logged in user
        user_id = session.get('user_id')

        # The initial measurements until set
        roomTemperature = 0
        airPressure = 0
        airHumidity = 0

        try:
            sql = """
                SELECT Temp, Press, Humid, Time
                FROM Sense 
                WHERE IP = INET_ATON(%s) 
                ORDER BY Time DESC;
            """

            # Get current Sense HAT data from DB
            self.database_cursor.execute(sql, (ip,))
            temp, press, humid, time = self.database_cursor.fetchone()

            # Convert to proper formatting
            roomTemperature = "{:.2f}".format(temp)
            airPressure = "{:.2f}".format(press)
            airHumidity = "{:.2f}".format(humid)
            
            try:
                if (triggerSettings_temperature != '') and (float(roomTemperature) > float(triggerSettings_temperature)):
                    # Write temperature data to database
                    sql = """
                        INSERT INTO eventlog 
                        (user_id, alert_time, alert_type, alert_message) 
                        VALUES (%s, NOW(), %s, %s);
                    """
                    message = name + " Temperature exceeded " + triggerSettings_temperature + " F"
    
                    self.database_cursor.execute(sql, (user_id, "Temperature", message))
                    self.database_connection.commit()
            
            except:
                # Catch and continue on invalid literal to convert to float errors in trigger settings
                pass

            try:
                if (triggerSettings_pressure != '') and (float(airPressure) > float(triggerSettings_pressure)):
                    # Write pressure data to database
                    sql = """
                        INSERT INTO eventlog 
                        (user_id, alert_time, alert_type, alert_message) 
                        VALUES (%s, NOW(), %s, %s);
                    """
                    message = name + " Pressure exceeded " + triggerSettings_pressure + " millibars"
    
                    self.database_cursor.execute(sql, (user_id, "Pressure", message))
                    self.database_connection.commit()
                    
            except:
                # Catch and continue on invalid literal to convert to float errors in trigger settings
                pass
            
            
            try:
                if (triggerSettings_humidity != '') and (float(airHumidity) > float(triggerSettings_humidity)):
                    # Write humidity data to database
                    sql = """
                        INSERT INTO eventlog 
                        (user_id, alert_time, alert_type, alert_message) 
                        VALUES (%s, NOW(), %s, %s);
                    """
                    message = name + " Humidity exceeded " + triggerSettings_humidity + " %"
                    self.database_cursor.execute(sql, (user_id, "Humidity", message))
                    self.database_connection.commit()
                    
            except:
                # Catch and continue on invalid literal to convert to float errors in trigger settings
                pass

        except Exception as e:
            pass