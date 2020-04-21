from app.controllers.controller import Controller

from datetime import datetime
from flask import Response
import pytz

class SessionController(Controller):
    def end_session(self, session_id):
        sql =  """UPDATE Session SET EndDate = %s WHERE id = %s"""
        dt = datetime.now().astimezone(pytz.timezone("America/Detroit"))
        self.database_cursor.execute(sql, (dt, session_id))
        self.database_connection.commit()

        return Response()



    def delete_session(self, session_id):
        self.database_cursor.execute('''DELETE FROM Session WHERE id = %s''', (session_id,))
        self.database_cursor.execute('''DELETE FROM SessionSensor WHERE SessionId = %s''', (session_id,))
        self.database_connection.commit()

        return Response()