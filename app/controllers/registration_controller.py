from app.controllers.controller import Controller
from app import bcrypt
from app.views.forms import RegistrationForm

from flask import session, flash

class RegistrationController(Controller):
    def handle_response(self):
        form = RegistrationForm()

        if form.password.data != form.password_confirm.data:
            flash("Password confirmation and password need to be the same")
            return self.redirect('registration')

        # Password Hashing
        inputted_password = form.password.data
        pw_hash = bcrypt.generate_password_hash(inputted_password).decode('utf-8')

        username = form.username.data

        self.database_cursor.execute('''CREATE TABLE IF NOT EXISTS user (id INTEGER UNSIGNED AUTO_INCREMENT PRIMARY KEY , username VARCHAR(60), hashed_pw TEXT)''')
        sql = "INSERT INTO user (username, hashed_pw) VALUES (%s, %s)"
        self.database_cursor.execute(sql, (username, pw_hash))

        self.database_connection.commit()

        return self.redirect('login')