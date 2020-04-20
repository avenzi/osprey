from app.views.view import View

from datetime import datetime, timedelta
from flask import session
import pytz

class EventlogView(View):
    def get_closest_items(self, time, adjustment, mintime):
        # The id of the logged in user
        user_id = session.get('user_id')

        # Return the latest 15 event log entries for this user
        sql = """
            SELECT alert_message, alert_time
            FROM eventlog
            WHERE user_id = %s AND alert_time < %s AND alert_time > %s
            ORDER BY alert_time DESC
            LIMIT 15;
        """
        dt = datetime.fromtimestamp(time / 1000).astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
        dt_min = datetime.fromtimestamp(mintime / 1000)
        dt_min = dt_min.astimezone(pytz.timezone("America/Detroit")) + timedelta(hours=adjustment)
        self.database_cursor.execute(sql, (user_id, dt, dt_min))
        results = self.database_cursor.fetchall()

        alerts = []
        for alert in results :
            alerts.append("{} at {}".format(alert[0], alert[1]))
        
        return self.render('snippets/eventlog_snippet.html', messages=alerts)

