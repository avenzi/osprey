import time
import datetime
import pytz

from database import Database

class SessionMonitor():

    def __init__(self):
        self.database_connection, self.database_cursor = Database().get_connection()
        self.find_latest_session()
    
    def find_latest_session(self):
        sql = """SELECT MAX(StartDate) FROM Session;"""
        self.database_cursor.execute(sql)
        result = self.database_cursor.fetchone()
        self.latest_session_start_time = -1 if result == None else result["MAX(StartDate)"]
    
    def block_until_new_session(self):
        print("-- Waiting until a new Session is started --")

        sql = """SELECT * FROM Session WHERE StartDate = (SELECT MAX(StartDate) FROM Session)"""
        while True:
            try:
                self.database_cursor.execute(sql)
                session_record = self.database_cursor.fetchone()
                max_start_time = session_record["StartDate"]
            except:
                max_start_time = None

            if max_start_time != None:
                if max_start_time > self.latest_session_start_time:
                    return session_record
            
            time.sleep(0.5)
    
    def block_until_end(self, session):
        sql = """SELECT EndDate FROM Session WHERE id = %s"""
        while True:
            time.sleep(0.5)
            end_date = None
            try:
                self.database_cursor.execute(sql, (session["id"],))
                session_record = self.database_cursor.fetchone()
                end_date = session_record["EndDate"]
            except:
                pass
            if end_date != None:
                break

