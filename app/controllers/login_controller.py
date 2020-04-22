from app.controllers.controller import Controller
from app import bcrypt
from app.views.forms import LoginForm

from flask import session

class LoginController(Controller):
    def handle_response(self):
        form = LoginForm()

        self.database_cursor.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER UNSIGNED AUTO_INCREMENT PRIMARY KEY , username VARCHAR(60), hashed_pw TEXT)''')
        self.database_connection.commit()

        self.database_cursor.execute("SELECT * FROM user where username = "+"'"+form.username.data+"'")

        result = self.database_cursor.fetchone()
        if result == None:
            return self.redirect("login")

        hashed_pw_from_db = result[2]
        user_input_pw = form.password.data
        correction_password = bcrypt.check_password_hash(hashed_pw_from_db, user_input_pw)

        if correction_password == False:
            return self.redirect("login")
        else:
            # Storing the username of a user in the session
            session["username"] = form.username.data

            global loginStatus
            loginStatus = True

            # Storing the id of the user that is logging in in the session
            self.database_cursor.execute("SELECT id FROM user WHERE username = "+"'"+session.get('username')+"'")
            session["user_id"] = self.database_cursor.fetchone()[0]

            # Creating session variables for the scalar trigger settings
            session["triggerSettings_temperature"] = ""
            session["triggerSettings_pressure"] = ""
            session["triggerSettings_humidity"] = ""

            # Creating the eventlog table if it does not exist. The eventlog table keeps track of all trigger events
            sql = """CREATE TABLE IF NOT EXISTS eventlog(
                id INTEGER UNSIGNED AUTO_INCREMENT,
                user_id INTEGER UNSIGNED,
                alert_time DATETIME,
                alert_type VARCHAR(255),
                alert_message VARCHAR(1023),
                PRIMARY KEY (id),
                FOREIGN KEY (user_id) REFERENCES user(id)
            );"""
            self.database_cursor.execute(sql)

            # Creating the Algorithm table if it does not exist. The Algorithm table keeps track of all algorithm information
            sql = """CREATE TABLE IF NOT EXISTS Algorithm(
                id INTEGER UNSIGNED AUTO_INCREMENT,
                UserId INTEGER UNSIGNED,
                Status BOOLEAN,
                Name VARCHAR(255),
                Path VARCHAR(255),
                PRIMARY KEY (id),
                FOREIGN KEY (UserId) REFERENCES user(id)
                );"""
            self.database_cursor.execute(sql)
            self.database_connection.commit()
            
            return self.redirect("home")