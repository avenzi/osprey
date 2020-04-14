from app.views.view import View

class HomeView(View):
    def get_rendered_template(self):
        self.database_cursor.execute("""SELECT id, StartDate, EndDate FROM Session ORDER BY StartDate DESC LIMIT 10;""")
        result = self.database_cursor.fetchall()

        sessions_view_data = []
        for session_data in result:
            data = {}
            session_id = session_data[0]
            data['name'] = 'Session #' + str(session_data[0])
            data['id'] = session_data[0]

            start_date = session_data[1].strftime("%m/%d/%Y %H:%M:%S")
            end_date = session_data[2]

            if end_date == None:
                end_date = "Ongoing"
            else:
                end_date = end_date.strftime("%m/%d/%Y %H:%M:%S")
            
            data['start_date'] = start_date
            data['end_date'] = end_date

            self.database_cursor.execute("""SELECT id, Name, INET_NTOA(IP), SessionId, SensorType FROM SessionSensor WHERE SessionId = %s;""", (session_id,))
            session_sensors = self.database_cursor.fetchall()

            list_of_sensors = ''
            first = True
            for sensor in session_sensors:
                if not first:
                    list_of_sensors = list_of_sensors + ', '
                list_of_sensors = list_of_sensors + sensor[1]
                first = False
            
            data['sensor_list'] = list_of_sensors
            sessions_view_data.append(data)

        return self.render('home.html', sessions_view_data=sessions_view_data)

