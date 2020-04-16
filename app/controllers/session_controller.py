from app.controllers.controller import Controller

from flask import Response

class SessionController(Controller):

    def delete_session(self, session_id):
        self.database_cursor.execute('''DELETE FROM Session WHERE id = %s''', (session_id,))
        self.database_cursor.execute('''DELETE FROM SessionSensor WHERE SessionId = %s''', (session_id,))
        self.database_connection.commit()

        return Response()