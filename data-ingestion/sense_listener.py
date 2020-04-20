from listener import Listener
import time
import json
import pymysql.cursors


###############################################
# SenseListener  : Listener class to handle SENSE Hat stream from Raspberry Pi
###############################################
class SenseListener(Listener, object):

    ###############################################
    # post_request  : handle post call from the SENSE Hat stream
    ###############################################
    def post_request(self, headers, data):
        # Interpret data for the database
        data_str = data.decode('utf-8')
        list_data = [d.split("=") for d in data_str.split("&")]
        temp = round(float(list_data[0][1]), 4)
        press = round(float(list_data[1][1]), 4)
        humid = round(float(list_data[2][1]), 4)

        ip = self.client_address[0]

        sql = """SELECT * FROM Session WHERE StartDate = (SELECT MAX(StartDate) FROM Session)"""
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        session_id = result['id']

        sql = """SELECT * FROM SessionSensor WHERE SessionId = %s AND SensorType = 'SenseHat'"""
        self.cursor.execute(sql, (session_id))
        result = self.cursor.fetchone()

        if result is None:
            return

        sensor_id = result['id']
        # Write data to database
        sql = "INSERT INTO `Sense` (`Time`, `IP`, `Temp`, `Press`, `Humid`, `SessionId`, `SensorId`) VALUES (NOW(3), INET_ATON(%s), %s, %s, %s, %s, %s)"
        self.cursor.execute(sql, (ip, temp, press, humid, session_id, sensor_id))
        self.db_connection.commit()